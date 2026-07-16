#!/usr/bin/env python3
"""
Ultra-simple system test - just checks if documents are processed and RAG pipeline responds.
Zero evaluation metrics to conserve API quota completely.
"""

import os
import sys
import asyncio
import json
import uuid

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.dependencies import async_session_factory
from app.models.db import Document, Session, Message
from app.agents.graph import compiled_graph

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def test_system_basics():
    """Verify the basic system works: docs processed, pipeline responds."""

    logger.info("=== SYSTEM BASIC FUNCTIONALITY TEST ===")

    # 1. Check documents in database
    async with async_session_factory() as db:
        stmt = select(Document)
        res = await db.execute(stmt)
        docs = res.scalars().all()

    logger.info(f"Found {len(docs)} documents in database:")
    ready_docs = [d for d in docs if d.status == "ready"]
    processing_docs = [d for d in docs if d.status == "processing"]
    error_docs = [d for d in docs if d.status == "error"]

    logger.info(f"  Ready: {len(ready_docs)}")
    logger.info(f"  Processing: {len(processing_docs)}")
    logger.info(f"  Error: {len(error_docs)}")

    if len(ready_docs) == 0:
        logger.error("No ready documents! Please run ingestion first.")
        return False

    # Show sample documents
    for doc in ready_docs[:3]:  # Show first 3
        logger.info(f"  - {doc.filename} ({doc.status})")

    # 2. Test a simple query against the first ready document
    test_doc = ready_docs[0]
    logger.info(f"\nTesting query against: {test_doc.filename}")

    test_questions = [
        "What is this document about?",  # Very general
        "What is the main topic?",       # General
        "Give me a brief summary."       # Summary request
    ]

    session_id = uuid.uuid4()

    # Create session
    async with async_session_factory() as db:
        new_session = Session(id=session_id, title="System Test")
        db.add(new_session)
        await db.commit()

    all_passed = True

    for i, question in enumerate(test_questions, 1):
        logger.info(f"\n--- Test {i}/{len(test_questions)}: '{question}' ---")

        try:
            # Setup minimal state
            initial_state = {
                "user_query": question,
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
                "trace_id": str(uuid.uuid4())
            }

            # Process through RAG pipeline
            async with async_session_factory() as db:
                # Add user message
                user_msg = Message(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    role="user",
                    content=question
                )
                db.add(user_msg)
                await db.commit()

                config = {
                    "configurable": {
                        "db": db,
                        "document_ids": [test_doc.id],
                        "langsmith_url": None
                    }
                }

                final_state = await compiled_graph.ainvoke(initial_state, config)

            answer = final_state.get("generated_answer", "")
            chunks = final_state.get("retrieved_chunks", [])

            logger.info(f"Answer: {len(answer)} characters")
            logger.info(f"Retrieved chunks: {len(chunks)}")

            if len(answer.strip()) > 0:
                # Show brief preview
                preview = answer.strip()[:150]
                if len(answer.strip()) > 150:
                    preview += "..."
                logger.info(f"Answer preview: {preview}")
                logger.info("✓ PASS: Got non-empty response")
            else:
                logger.warning("✗ FAIL: Empty response")
                all_passed = False

        except Exception as e:
            logger.error(f"✗ FAIL: Exception occurred: {e}")
            all_passed = False

    logger.info(f"\n=== TEST COMPLETE ===")
    if all_passed:
        logger.info("✓ All basic tests passed - system appears functional")
        logger.info("  (Note: This does not verify answer correctness, only that pipeline responds)")
    else:
        logger.info("✗ Some tests failed - check logs above")

    return all_passed

async def main():
    success = await test_system_basics()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
