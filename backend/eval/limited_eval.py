#!/usr/bin/env python3
"""
Limited evaluation script that runs only a small subset of questions
to conserve API quota while verifying system functionality.
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

async def run_limited_evaluation(max_questions: int = 3):
    """Run evaluation on only the first N questions to save quota."""

    # 1. Load evaluation dataset
    dataset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_dataset.json")
    if not os.path.exists(dataset_path):
        # Fallback to root workspace location
        dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "eval", "eval_dataset.json")

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    questions = dataset.get("questions", [])[:max_questions]  # LIMIT TO FIRST N QUESTIONS
    logger.info(f"Loaded {len(questions)} evaluation Q&A pairs (limited from {len(dataset.get('questions', []))} total)")

    # 2. Get document maps from database
    doc_map = {}
    async with async_session_factory() as db:
        stmt = select(Document)
        res = await db.execute(stmt)
        docs = res.scalars().all()
        for d in docs:
            # Match by filename
            doc_map[d.filename] = d.id
            logger.info(f"Mapped document: '{d.filename}' -> {d.id}")

    # Verify we have the required papers
    required_files = set(q["filename"] for q in questions)
    missing = [f for f in required_files if f not in doc_map]
    if missing:
        logger.error(f"Missing required papers in database: {missing}")
        return

    # 3. Create session for all questions (reuse same session to save calls)
    session_id = uuid.uuid4()
    async with async_session_factory() as db:
        new_session = Session(id=session_id, title=f"Limited Eval ({len(questions)} questions)")
        db.add(new_session)
        await db.commit()

    results = []
    total_questions = len(questions)

    # 4. Process each question
    for idx, q_item in enumerate(questions):
        query = q_item["query"]
        filename = q_item["filename"]
        ground_truth = q_item["ground_truth"]
        doc_id = doc_map[filename]

        logger.info(f"\n[{idx + 1}/{total_questions}] Processing: '{query[:60]}...'")

        # Setup initial LangGraph state
        trace_id = uuid.uuid4()
        initial_state = {
            "user_query": query,
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

        try:
            # Execute RAG flow
            async with async_session_factory() as db:
                # Add user message
                user_msg = Message(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    role="user",
                    content=query
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

            # Basic metrics (no extra LLM calls to save quota)
            answer_length = len(generated_answer)
            has_answer = answer_length > 10  # Consider non-trivial answer

            result = {
                "question": query,
                "filename": filename,
                "answer_length": answer_length,
                "has_answer": has_answer,
                "num_chunks": len(retrieved_chunks),
                "success": has_answer  # Basic success criteria
            }

            results.append(result)

            if has_answer:
                preview = generated_answer[:100] + "..." if len(generated_answer) > 100 else generated_answer
                logger.info(f"✓ Success: {answer_length} chars, {len(retrieved_chunks)} chunks")
                logger.info(f"  Preview: {preview}")
            else:
                logger.warning(f"✗ Failed: Empty or too short answer ({answer_length} chars)")

        except Exception as e:
            logger.error(f"✗ Error processing question: {e}")
            results.append({
                "question": query,
                "filename": filename,
                "error": str(e),
                "success": False
            })

    # 5. Summary
    successful = sum(1 for r in results if r.get("success", False))
    logger.info(f"\n{'='*50}")
    logger.info(f"RESULTS: {successful}/{total_questions} questions successful")
    logger.info(f"Success rate: {successful/total_questions*100:.1f}%")
    logger.info(f"{'='*50}")

    # Save limited results
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "limited_eval_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "total_questions": total_questions,
            "successful_questions": successful,
            "success_rate": successful/total_questions if total_questions > 0 else 0,
            "results": results
        }, f, indent=2)
    logger.info(f"Results saved to {out_path}")

if __name__ == "__main__":
    # Default to 3 questions to be very conservative with quota
    max_q = 3
    if len(sys.argv) > 1:
        try:
            max_q = int(sys.argv[1])
            if max_q < 1:
                max_q = 1
            elif max_q > 10:  # Still cap at 10 to be safe
                max_q = 10
        except ValueError:
            pass

    print(f"Running limited evaluation with {max_q} question(s)...")
    print("This will minimize API quota usage while verifying system functionality.")
    asyncio.run(run_limited_evaluation(max_questions=max_q))
