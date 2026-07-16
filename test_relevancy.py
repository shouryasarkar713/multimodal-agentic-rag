import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from eval.metrics import evaluate_answer_relevancy

async def test():
    q = "What is the main contribution of the paper?"
    a = "The paper introduces a novel attention mechanism that improves transformer efficiency by 40%."
    score = await evaluate_answer_relevancy(q, a)
    print(f"Relevancy score: {score:.4f}")

asyncio.run(test())
