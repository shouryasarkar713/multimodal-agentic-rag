import pytest
import io
import uuid
import os
import fitz  # PyMuPDF
from unittest.mock import patch, MagicMock
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.db import Document, Chunk
from app.services.ingestion import run_ingestion_pipeline

# Create helper to generate a simple PDF dynamically in-memory
def create_test_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Introduction\nThis is the first page of our test document.", fontsize=11)
    page.insert_text((50, 100), "Section Heading\nThis is some bold technical text about neural networks.", fontsize=16)
    
    # Page 2 with table text
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Table 1: Hyperparameters\n| Parameter | Value |\n| --- | --- |\n| LR | 0.01 |\n| Epochs | 10 |", fontsize=11)
    
    # Page 3 with figure text
    page3 = doc.new_page()
    page3.insert_text((50, 50), "Figure 1: Architecture\nThis is a drawing of our transformer block.", fontsize=11)
    
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

@pytest.mark.asyncio
async def test_upload_endpoints_validation(client: AsyncClient):
    """Test X-API-Key and payload validation rules on document upload."""
    headers = {"X-API-Key": settings.api_key}
    
    # 1. Invalid API Key
    response = await client.post("/api/documents/upload", headers={"X-API-Key": "invalid"}, files={"file": ("test.pdf", b"pdfcontent")})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid API key"}
    
    # 2. Missing API Key
    response = await client.post("/api/documents/upload", files={"file": ("test.pdf", b"pdfcontent")})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid API key"}
    
    # 3. Not a PDF
    response = await client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("test.txt", b"plain text content", "text/plain")}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "File must be a PDF"}
    
    # 4. Empty file
    response = await client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("test.pdf", b"", "application/pdf")}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Uploaded file is empty."}

@pytest.mark.asyncio
@patch("app.services.ingestion.embed_text_batch")
@patch("app.services.ingestion.embed_image")
@patch("app.services.ingestion.caption_image")
async def test_ingestion_pipeline_success(
    mock_caption_image,
    mock_embed_image,
    mock_embed_text,
    client: AsyncClient,
    db_session: AsyncSession
):
    """Test full 10-step ingestion pipeline with mocked embedding and vision endpoints."""
    # Set up mocks
    mock_embed_text.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]
    mock_embed_image.return_value = [0.2] * 512
    mock_caption_image.return_value = "AI generated description of architectural chart."
    
    # 1. Generate test PDF and trigger upload
    pdf_data = create_test_pdf()
    headers = {"X-API-Key": settings.api_key}
    
    response = await client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("test.pdf", pdf_data, "application/pdf")}
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    res_data = response.json()
    assert res_data["status"] == "processing"
    doc_id = uuid.UUID(res_data["document_id"])
    
    # 2. Run ingestion pipeline synchronously to verify pipeline execution
    # (Since background tasks run asynchronously, we invoke it directly for unit testing)
    await run_ingestion_pipeline(doc_id)
    
    # 3. Assert document status is updated to 'ready'
    stmt = select(Document).where(Document.id == doc_id)
    doc_result = await db_session.execute(stmt)
    doc = doc_result.scalar_one()
    assert doc.status == "ready"
    assert doc.title is not None
    assert doc.total_pages == 3
    
    # 4. Assert chunk creation and embedding dimensions (1536 for text, 512 for image)
    chunk_stmt = select(Chunk).where(Chunk.document_id == doc_id)
    chunk_result = await db_session.execute(chunk_stmt)
    chunks = chunk_result.scalars().all()
    assert len(chunks) > 0
    
    for c in chunks:
        # Check text embeddings are 1536 dimension
        assert c.text_embedding is not None
        assert len(c.text_embedding) == 1536
        
        # Check image embeddings are 512 dimension
        if c.content_type == "image":
            assert c.image_embedding is not None
            assert len(c.image_embedding) == 512
            
    # Clean up physical test file saved in background upload
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
