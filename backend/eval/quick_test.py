#!/usr/bin/env python3
"""
Quick test script to verify the RAG system works within tight API quotas.
Runs only 1-2 questions with minimal LLM calls for evaluation.
"""

import os
import sys
import asyncio
import json
import uuid
from typing import List, Dict, Any

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.dependencies import async_session_factory
from app.models.db import Document, Session, Message
from app.agents.graph import compiled_graph

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def test_single_question(question_text: str, filename: str):
    """Test a single question and return basic success metrics."""
    logger.info(f"Testing question: '{question_text}'")

    # Get document map
    doc_map = {}
    async with async_session_factory() as db:
        stmt = select(Document)
        res = await db.execute(stmt)
        docs = res.scalars().all()
        for d in docs:
            doc_map[d.filename] = d.id

    if filename not in doc_map:
        logger.error(f"Document {filename} not found in database. Available: {list(doc_map.keys())}")
        return None

    doc_id = doc_map[filename]
    session_id = uuid.uuid4()
    trace_id = uuid.uuid4()

    # Create session
    async with async_session_factory() as db:
        new_session = Session(id=session_id, title="Quick Test")
        db.add(new_session)
        await db.commit()

    # Setup initial state
    initial_state = {
        "user_query": question_text,
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

    # Execute RAG flow
    try:
        async with async_session_factory() as db:
            # Add user message
            user_msg = Message(
                id=uuid.uuid4(),
                session_id=session_id,
                role="user",
                content=question_text
            )
            db.add(user_msg)
            await db.commit()

            config = {
                "configurable": {
                    "db": db,
                    "document_ids": [doc_id],
                    "langsmith_url": None
                }
            }

            final_state = await compiled_graph.ainvoke(initial_state, config)

        generated_answer = final_state.get("generated_answer", "")
        retrieved_chunks = final_state.get("retrieved_chunks") or []

        logger.info(f"Generated answer length: {len(generated_answer)} chars")
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks")

        # Basic validation - did we get an answer?
        success = len(generated_answer.strip()) > 0

        # Show first 200 chars of answer
        if generated_answer:
            preview = generated_answer[:200] + "..." if len(generated_answer) > 200 else generated_answer
            logger.info(f"Answer preview: {preview}")
        else:
            logger.warning("Empty answer generated!")

        return {
            "success": success,
            "answer": generated_answer,
            "num_chunks": len(retrieved_chunks),
            "question": question_text
        }

    except Exception as e:
        logger.error(f"Error processing question: {e}")
        return {"success": False, "error": str(e)}

async def main():
    """Run a quick test with just 1-2 questions to verify system functionality."""
    test_questions = [
        {
            "query": "What is the main contribution of the Transformer architecture?",
            "filename": "1706.03762.pdf"
        },
        {
            "query": "What is the shortcut connection concept in Deep Residual Learning?",
            "filename": "1512.03385.pdf"
        }
    ]

    results = []
    for q in test_questions:
        res = await test_single_question(q["query"], q["filename"])
        if res:
            results.append(res)

    success_count = sum(1 for r in results if r.get("success"))
    print(f"\nQuick test complete: {success_count}/{len(results)} queries succeeded.")

if __name__ == "__main__":
    asyncio.run(main())
