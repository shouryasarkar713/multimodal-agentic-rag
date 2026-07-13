import os
import sys
import asyncio
import json
import uuid
import logging
from typing import List, Dict, Any

# Adjust path to import from backend app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.dependencies import async_session_factory
from app.models.db import Document, Session, Message
from app.agents.graph import compiled_graph

from eval.metrics import (
    evaluate_faithfulness,
    evaluate_answer_relevancy,
    evaluate_context_precision,
    evaluate_citation_accuracy
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def run_evaluation():
    # 1. Load evaluation dataset
    dataset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_dataset.json")
    if not os.path.exists(dataset_path):
        # Fallback to root workspace location
        dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "eval", "eval_dataset.json")
        
    with open(dataset_path, "r") as f:
        dataset = json.load(f)
        
    questions = dataset.get("questions", [])
    logging.info(f"Loaded {len(questions)} evaluation Q&A pairs.")
    
    # 2. Get document maps from database
    doc_map = {}
    async with async_session_factory() as db:
        stmt = select(Document)
        res = await db.execute(stmt)
        docs = res.scalars().all()
        for d in docs:
            # Match by filename
            doc_map[d.filename] = d.id
            logging.info(f"Mapped document: '{d.filename}' -> {d.id}")
            
    # Verify we have all 3 papers ready
    missing = []
    for q in questions:
        fname = q["filename"]
        if fname not in doc_map:
            if fname not in missing:
                missing.append(fname)
                
    if missing:
        logging.error(f"Missing required papers in database: {missing}. Please make sure they are uploaded and ready first!")
        print(f"\n[ERROR] Missing documents: {missing}. Please trigger download_arxiv first.")
        return
        
    # 3. Create active session
    session_id = uuid.uuid4()
    async with async_session_factory() as db:
        new_session = Session(id=session_id, title="Evaluation Run")
        db.add(new_session)
        await db.commit()
        
    results = []
    
    # 4. Iterate over dataset
    for idx, q_item in enumerate(questions):
        query = q_item["query"]
        filename = q_item["filename"]
        ground_truth = q_item["ground_truth"]
        doc_id = doc_map[filename]
        
        logging.info(f"\n[{idx + 1}/30] Query: '{query}' (Target Doc: {filename})")
        
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
        
        # Invoke compiled graph inside database transaction
        async with async_session_factory() as db:
            # Manually append user message row so finalizing works
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
            
            # Execute RAG flow
            final_state = await compiled_graph.ainvoke(initial_state, config)
            
        generated_answer = final_state.get("generated_answer", "")
        retrieved_chunks = final_state.get("retrieved_chunks") or []
        context_texts = [
            c.get("content_text") or c.get("content_markdown") or c.get("image_caption") or ""
            for c in retrieved_chunks
        ]
        
        # 5. Evaluate Metrics
        logging.info("Calculating metrics...")
        faithfulness = await evaluate_faithfulness(generated_answer, context_texts)
        relevancy = await evaluate_answer_relevancy(query, generated_answer)
        precision = await evaluate_context_precision(query, context_texts)
        citation_acc = await evaluate_citation_accuracy(generated_answer, retrieved_chunks)
        
        logging.info(f"Scores -> Faithfulness: {faithfulness:.2f}, Relevancy: {relevancy:.2f}, Precision: {precision:.2f}, Citations: {citation_acc:.2f}")
        
        results.append({
            "query": query,
            "ground_truth": ground_truth,
            "generated_answer": generated_answer,
            "faithfulness": faithfulness,
            "relevancy": relevancy,
            "context_precision": precision,
            "citation_accuracy": citation_acc
        })
        
    # 6. Aggregate Scores
    total = len(results)
    mean_faithfulness = sum(r["faithfulness"] for r in results) / total
    mean_relevancy = sum(r["relevancy"] for r in results) / total
    mean_precision = sum(r["context_precision"] for r in results) / total
    mean_citations = sum(r["citation_accuracy"] for r in results) / total
    
    # 7. Format Terminal Report
    print("\n" + "=" * 50)
    print("           EVALUATION RESULTS REPORT")
    print("=" * 50)
    print(f"Total Evaluated Questions: {total}")
    print("-" * 50)
    print(f"Faithfulness:      {mean_faithfulness:.4f}  (Threshold: >= 0.85) {'[PASS]' if mean_faithfulness >= 0.85 else '[FAIL]'}")
    print(f"Answer Relevancy:  {mean_relevancy:.4f}  (Threshold: >= 0.80) {'[PASS]' if mean_relevancy >= 0.80 else '[FAIL]'}")
    print(f"Context Precision: {mean_precision:.4f}  (Threshold: >= 0.70) {'[PASS]' if mean_precision >= 0.70 else '[FAIL]'}")
    print(f"Citation Accuracy: {mean_citations:.4f}  (Threshold: >= 0.90) {'[PASS]' if mean_citations >= 0.90 else '[FAIL]'}")
    print("=" * 50)
    
    # Save results to file
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "mean_metrics": {
                "faithfulness": mean_faithfulness,
                "answer_relevancy": mean_relevancy,
                "context_precision": mean_precision,
                "citation_accuracy": mean_citations
            },
            "queries": results
        }, f, indent=2)
    logging.info(f"Saved evaluation results report to {out_path}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
