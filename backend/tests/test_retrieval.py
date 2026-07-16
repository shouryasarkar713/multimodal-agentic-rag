import pytest
import uuid
import torch
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.db import Document, Chunk, Session

@pytest.mark.asyncio
@patch("app.services.retrieval.get_cross_encoder")
@patch("app.services.retrieval.get_clip_model")
@patch("app.services.retrieval.get_embeddings_model")
async def test_retrieve_endpoint(
    mock_get_embeddings_model,
    mock_get_clip_model,
    mock_get_cross_encoder,
    client: AsyncClient,
    db_session: AsyncSession
):
    """Test hybrid search, multimodal CLIP matching, and re-ranking on the retrieve endpoint."""
    # 1. Setup Mocks
    # Mock Embeddings Model
    mock_embeddings_inst = MagicMock()
    mock_embeddings_inst.aembed_query = AsyncMock(return_value=[0.1] * 1536)
    mock_get_embeddings_model.return_value = mock_embeddings_inst
    
    # Mock CLIP Model
    mock_clip_model = MagicMock()
    mock_clip_features = torch.ones((1, 512))
    mock_clip_model.encode_text.return_value = mock_clip_features
    mock_get_clip_model.return_value = (mock_clip_model, MagicMock())
    
    # Mock CrossEncoder
    mock_ce = MagicMock()
    # Mock scores for 3 candidates
    mock_ce.predict.return_value = [0.95, 0.45, 0.85]
    mock_get_cross_encoder.return_value = mock_ce
    
    # 2. Insert dummy Document and Chunks in DB
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        filename="attention.pdf",
        title="Attention Is All You Need",
        total_pages=15,
        file_path="/data/uploads/attention.pdf",
        file_size_bytes=1024,
        status="ready"
    )
    db_session.add(doc)
    
    # Text chunk
    chunk_text = Chunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        content_type="text",
        content_text="Neural machine translation has achieved state of the art results.",
        page_number=1,
        chunk_index=0,
        section_title="Abstract",
        text_embedding=[0.1] * 1536
    )
    # Table chunk
    chunk_table = Chunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        content_type="table",
        content_text="| Model | BLEU |\n| --- | --- |\n| Base | 27.3 |",
        content_markdown="| Model | BLEU |\n| --- | --- |\n| Base | 27.3 |",
        page_number=8,
        chunk_index=1,
        section_title="Results",
        text_embedding=[0.1] * 1536
    )
    # Image chunk
    chunk_image = Chunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        content_type="image",
        content_text="Figure 1: The Transformer model architecture.",
        image_path="/data/images/transformer_architecture.png",
        image_caption="Flow diagram showing scaled dot-product attention.",
        page_number=3,
        chunk_index=2,
        section_title="Model Architecture",
        text_embedding=[0.1] * 1536,
        image_embedding=[1.0] * 512
    )
    
    db_session.add_all([chunk_text, chunk_table, chunk_image])
    await db_session.flush()
    
    # 3. Call POST /api/chat/retrieve
    headers = {"X-API-Key": settings.api_key}
    request_data = {
        "query": "transformer model architecture",
        "document_id": str(doc_id),
        "top_k": 3
    }
    
    response = await client.post(
        "/api/chat/retrieve",
        headers=headers,
        json=request_data
    )
    
    assert response.status_code == status.HTTP_200_OK
    res_data = response.json()
    assert "chunks" in res_data
    chunks = res_data["chunks"]
    
    # Assert we got the chunks and they were re-ranked based on CrossEncoder mock scores
    # Scores returned: text=0.95, table=0.45, image=0.85
    # Sorted order should be: text (0.95), image (0.85), table (0.45)
    assert len(chunks) == 3
    assert chunks[0]["content_type"] == "text"
    assert chunks[1]["content_type"] == "image"
    assert chunks[1]["image_url"] == "/api/images/transformer_architecture.png"
    assert chunks[2]["content_type"] == "table"

@pytest.mark.asyncio
async def test_session_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """Test Chat Sessions CRUD lifecycle endpoints."""
    headers = {"X-API-Key": settings.api_key}
    
    # 1. Create session
    response = await client.post(
        "/api/sessions",
        headers=headers,
        json={"title": "NLP Discussion"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    res_data = response.json()
    assert res_data["title"] == "NLP Discussion"
    session_id = res_data["id"]
    
    # 2. List sessions
    response = await client.get("/api/sessions", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    list_data = response.json()
    assert len(list_data["sessions"]) >= 1
    assert any(s["id"] == session_id for s in list_data["sessions"])
    
    # 3. Delete session
    response = await client.delete(f"/api/sessions/{session_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Session deleted successfully"}
