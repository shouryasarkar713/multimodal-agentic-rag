import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.agents.nodes.query_understanding import query_understanding_node
from app.agents.nodes.intent_router import route_by_intent
from app.agents.graph import compiled_graph

@pytest.mark.asyncio
@patch("app.agents.nodes.query_understanding.ChatOpenAI")
async def test_query_understanding_parsing(mock_chat_openai_class):
    """Test that query_understanding node correctly parses structured JSON response from LLM."""
    mock_llm_inst = MagicMock()
    mock_llm_inst.ainvoke = AsyncMock(return_value=MagicMock(
        content='{"intent": "compare", "query_text": "transformer vs resnet", "target_papers": ["Paper A", "Paper B"], "figure_ref": null, "section_ref": "Section 4.1", "retrieval_types": ["text", "table"]}'
    ))
    mock_chat_openai_class.return_value = mock_llm_inst
    
    state = AgentState(
        user_query="compare transformer vs resnet in Section 4.1",
        session_id=str(uuid.uuid4()),
        chat_history=[],
        classified_intent=None,
        parsed_query=None,
        retrieval_types=[],
        retrieved_chunks=[],
        formatted_context="",
        retrieval_attempt=0,
        rewritten_query=None,
        sub_queries=[],
        sub_results=[],
        evidence_scores=[],
        evidence_sufficient=False,
        generated_answer="",
        citations=[],
        figure_refs=[],
        confidence_score=1.0,
        validation_passed=None,
        validation_issues=[],
        trace_steps=[],
        trace_id=str(uuid.uuid4())
    )
    
    res = await query_understanding_node(state)
    assert res["classified_intent"] == "compare"
    assert res["parsed_query"]["query_text"] == "transformer vs resnet"
    assert "Section 4.1" in res["parsed_query"]["section_ref"]
    assert "table" in res["retrieval_types"]
    assert len(res["trace_steps"]) == 1

def test_intent_routing():
    """Verify routing edge returns the correct path branch based on intent."""
    state_qa = AgentState(classified_intent="paper_qa")
    state_compare = AgentState(classified_intent="compare")
    state_empty = AgentState(classified_intent=None)
    
    assert route_by_intent(state_qa) == "paper_qa"
    assert route_by_intent(state_compare) == "compare"
    assert route_by_intent(state_empty) == "paper_qa"

@pytest.mark.asyncio
@patch("app.agents.nodes.retrieval_orchestrator.get_embeddings_model")
@patch("app.agents.nodes.retrieval_orchestrator.get_cross_encoder")
@patch("app.agents.nodes.finalize.AsyncSession")
@patch("app.agents.nodes.generator.ChatOpenAI")
@patch("app.agents.nodes.query_rewriter.ChatOpenAI")
@patch("app.agents.nodes.evidence_grader.ChatOpenAI")
@patch("app.agents.nodes.query_understanding.ChatOpenAI")
async def test_agent_retry_loop_capping(
    mock_qu_llm_class,
    mock_eg_llm_class,
    mock_qr_llm_class,
    mock_gen_llm_class,
    mock_session_class,
    mock_get_cross_encoder,
    mock_get_embeddings_model
):
    """Test that the evidence-grader retry loop triggers query_rewriter and caps retries at 2."""
    # 1. Setup mock embeddings and cross-encoder
    mock_embed = MagicMock()
    mock_embed.aembed_query = AsyncMock(return_value=[0.1] * 1536)
    mock_get_embeddings_model.return_value = mock_embed
    
    mock_ce = MagicMock()
    mock_ce.predict.return_value = [0.8] * 2
    mock_get_cross_encoder.return_value = mock_ce
    
    # 2. Setup mock LLM responses for each graph stage
    # Query understanding mock
    mock_qu_llm = MagicMock()
    mock_qu_llm.ainvoke = AsyncMock(return_value=MagicMock(
        content='{"intent": "paper_qa", "query_text": "transformer", "target_papers": [], "figure_ref": null, "section_ref": null, "retrieval_types": ["text"]}'
    ))
    mock_qu_llm_class.return_value = mock_qu_llm
    
    # Evidence grader mock: return low scores (e.g. 3.0, 1.0) to force retry
    mock_eg_llm = MagicMock()
    mock_eg_llm.ainvoke = AsyncMock(return_value=MagicMock(
        content='[{"chunk_index": 0, "score": 3.0, "reason": "ok"}, {"chunk_index": 1, "score": 1.0, "reason": "poor"}]'
    ))
    mock_eg_llm_class.return_value = mock_eg_llm
    
    # Query rewriter mock
    mock_qr_llm = MagicMock()
    mock_qr_llm.ainvoke = AsyncMock(return_value=MagicMock(
        content="new query search keywords"
    ))
    mock_qr_llm_class.return_value = mock_qr_llm
    
    # Generator mock
    mock_gen_llm = MagicMock()
    mock_gen_llm.ainvoke = AsyncMock(return_value=MagicMock(
        content="This is the final answer [1]."
    ))
    mock_gen_llm_class.return_value = mock_gen_llm
    
    # 3. Create dummy database session
    mock_db = MagicMock(spec=AsyncSession)
    
    # Mock database queries inside retrieval_orchestrator
    # We yield dummy chunk objects
    mock_chunk_1 = MagicMock()
    mock_chunk_1.id = uuid.uuid4()
    mock_chunk_1.document_id = uuid.uuid4()
    mock_chunk_1.content_type = "text"
    mock_chunk_1.content_text = "attention is all you need text"
    mock_chunk_1.page_number = 1
    mock_chunk_1.section_title = "Abstract"
    
    mock_chunk_2 = MagicMock()
    mock_chunk_2.id = uuid.uuid4()
    mock_chunk_2.document_id = uuid.uuid4()
    mock_chunk_2.content_type = "text"
    mock_chunk_2.content_text = "multi-head self-attention text"
    mock_chunk_2.page_number = 2
    mock_chunk_2.section_title = "Architecture"
    
    mock_db_result = MagicMock()
    mock_db_result.scalars.return_value.all.return_value = [mock_chunk_1, mock_chunk_2]
    mock_db.execute = AsyncMock(return_value=mock_db_result)
    
    # Mock document details select
    mock_doc_result = MagicMock()
    mock_doc_result.all.return_value = [(mock_chunk_1.document_id, "Transformer Paper", "transformer.pdf")]
    mock_db.execute = AsyncMock(side_effect=[
        mock_db_result,  # dense
        mock_db_result,  # sparse
        mock_doc_result, # doc details
        mock_db_result,  # dense retry 1
        mock_db_result,  # sparse retry 1
        mock_doc_result, # doc details retry 1
        mock_db_result,  # dense retry 2
        mock_db_result,  # sparse retry 2
        mock_doc_result  # doc details retry 2
    ])
    
    # 4. Invoke graph
    session_id = uuid.uuid4()
    trace_id = uuid.uuid4()
    
    initial_state = {
        "user_query": "What optimizer does the transformer use?",
        "session_id": str(session_id),
        "chat_history": [],
        "classified_intent": None,
        "parsed_query": None,
        "retrieval_types": [],
        "retrieved_chunks": [],
        "formatted_context": "",
        "retrieval_attempt": 0,
        "rewritten_query": None,
        "sub_queries": [],
        "sub_results": [],
        "evidence_scores": [],
        "evidence_sufficient": False,
        "generated_answer": "",
        "citations": [],
        "figure_refs": [],
        "confidence_score": 1.0,
        "validation_passed": None,
        "validation_issues": [],
        "trace_steps": [],
        "trace_id": str(trace_id)
    }
    
    config = {
        "configurable": {
            "db": mock_db,
            "document_ids": [],
            "langsmith_url": None
        }
    }
    
    final_state = await compiled_graph.ainvoke(initial_state, config)
    
    # Assert retry attempts reached max value 2 (capping mechanism)
    assert final_state["retrieval_attempt"] == 2
    # Verify that the generation succeeded (best effort)
    assert final_state["evidence_sufficient"] is True
    assert "final answer" in final_state["generated_answer"].lower()
    
    # Verify db commits were made (finalize node)
    assert mock_db.commit.called
