import re
import json
import logging
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import settings

def get_eval_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=settings.openai_api_key,
        temperature=0.0
    )

def get_eval_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key
    )

async def evaluate_faithfulness(answer: str, context_chunks: List[str]) -> float:
    """
    Check if the claims in the generated answer are supported by the retrieved context.
    Faithfulness = (number of supported claims) / (total claims in the answer).
    """
    if not answer.strip():
        return 0.0
    
    llm = get_eval_llm()
    context_str = "\n\n".join([f"Chunk {i+1}:\n{chunk}" for i, chunk in enumerate(context_chunks)])
    
    # Step 1: Extract claims
    extract_prompt = f"""
Given a generated answer, extract all distinct factual claims made in it as a JSON list of strings.
Do not extract questions or generic statements, only specific factual claims.

Generated Answer:
{answer}

Respond ONLY with a valid JSON array of strings. Example:
["The model uses AdamW optimizer", "BERT achieved 82.1% on GLUE"]
"""
    try:
        res = await llm.ainvoke(extract_prompt)
        content = res.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        claims = json.loads(content.strip())
        
        if not claims:
            return 1.0 # No claims made means no hallucinated claims
            
        # Step 2: Verify each claim against context
        supported_count = 0
        for claim in claims:
            verify_prompt = f"""
Analyze if the following Claim is directly supported by the provided Context. 
The claim is supported if it is explicitly stated or can be directly inferred from the Context.

Context:
{context_str}

Claim:
{claim}

Respond with exactly 'YES' if the claim is fully supported by the context, or 'NO' if it is not supported or contradicted. Do not write anything else.
"""
            verify_res = await llm.ainvoke(verify_prompt)
            verdict = verify_res.content.strip().upper()
            if 'YES' in verdict:
                supported_count += 1
                
        return supported_count / len(claims)
    except Exception as e:
        logging.error(f"Error in evaluate_faithfulness: {e}")
        return 0.5 # Neutral fallback

async def evaluate_answer_relevancy(question: str, answer: str) -> float:
    """
    Measures how relevant the generated answer is to the user question.
    Generates 3 questions that the answer could answer, embeds them,
    and computes the average cosine similarity with the original question embedding.
    """
    if not answer.strip():
        return 0.0
        
    llm = get_eval_llm()
    embeddings = get_eval_embeddings()
    
    prompt = f"""
Given the following generated answer, write exactly 3 distinct, search-like questions that this answer could directly answer.
Do not include any other text or explanation.

Generated Answer:
{answer}

Respond with exactly 3 questions, one per line.
"""
    try:
        res = await llm.ainvoke(prompt)
        lines = [line.strip() for line in res.content.strip().split('\n') if line.strip()]
        generated_questions = lines[:3]
        
        if not generated_questions:
            return 0.0
            
        # Embed all questions
        user_q_emb = await embeddings.aembed_query(question)
        gen_embs = await embeddings.aembed_documents(generated_questions)
        
        # Calculate average cosine similarity
        import numpy as np
        similarities = []
        u_norm = np.linalg.norm(user_q_emb)
        for g_emb in gen_embs:
            g_norm = np.linalg.norm(g_emb)
            if u_norm > 0 and g_norm > 0:
                cos_sim = np.dot(user_q_emb, g_emb) / (u_norm * g_norm)
                similarities.append(float(cos_sim))
                
        return sum(similarities) / len(similarities) if similarities else 0.0
    except Exception as e:
        logging.error(f"Error in evaluate_answer_relevancy: {e}")
        return 0.5

async def evaluate_context_precision(question: str, retrieved_chunks: List[str]) -> float:
    """
    Evaluates if the retrieved chunks containing relevant information are ranked at the top.
    Context Precision = (Sum_k (Precision@k * relevance(k))) / (Total relevant chunks in retrieved set).
    """
    if not retrieved_chunks:
        return 0.0
        
    llm = get_eval_llm()
    relevance_scores = []
    
    # Classify relevance for each chunk
    for chunk in retrieved_chunks:
        prompt = f"""
Determine if the following retrieved chunk contains relevant information that helps answer the user's question.

Question:
{question}

Retrieved Chunk:
{chunk}

Respond with exactly 'YES' if relevant, or 'NO' if it is not relevant. Do not write anything else.
"""
        try:
            res = await llm.ainvoke(prompt)
            verdict = res.content.strip().upper()
            relevance_scores.append(1 if 'YES' in verdict else 0)
        except Exception:
            relevance_scores.append(0)
            
    # Calculate Precision@k and Context Precision
    num_relevant = sum(relevance_scores)
    if num_relevant == 0:
        return 0.0
        
    precision_sum = 0.0
    relevant_so_far = 0
    
    for k, is_relevant in enumerate(relevance_scores):
        if is_relevant == 1:
            relevant_so_far += 1
            precision_at_k = relevant_so_far / (k + 1)
            precision_sum += precision_at_k
            
    return precision_sum / num_relevant

async def evaluate_citation_accuracy(answer: str, retrieved_chunks: List[Dict[str, Any]]) -> float:
    """
    Verify that every cited claim [N] is supported by the N-th retrieved chunk.
    Citation Accuracy = (number of correctly cited claims) / (total citations [N] in the answer).
    """
    # Find all inline citations [N]
    citations = re.findall(r'\[(\d+)\]', answer)
    if not citations:
        return 1.0 # 100% accurate if no citations are hallucinated or needed
        
    llm = get_eval_llm()
    correct_count = 0
    total_citations = 0
    
    # Split answer by sentences to analyze cited sentences
    sentences = re.split(r'(?<=[.!?])\s+', answer)
    
    for sentence in sentences:
        matches = re.findall(r'\[(\d+)\]', sentence)
        if not matches:
            continue
            
        # Analyze claim for each matching citation number
        for match in matches:
            idx = int(match) - 1
            total_citations += 1
            
            # If citation index exceeds retrieved chunks, it's incorrect (hallucination)
            if idx < 0 or idx >= len(retrieved_chunks):
                continue
                
            chunk = retrieved_chunks[idx]
            chunk_content = chunk.get("content_text") or chunk.get("content_markdown") or chunk.get("excerpt") or ""
            
            # Use LLM to verify if this specific sentence is supported by this chunk
            prompt = f"""
Verify if the cited claim is fully supported by the reference chunk.

Reference Chunk:
{chunk_content}

Cited Claim:
{sentence}

Respond with exactly 'YES' if the reference chunk supports the claim, or 'NO' if it does not. Do not write anything else.
"""
            try:
                res = await llm.ainvoke(prompt)
                verdict = res.content.strip().upper()
                if 'YES' in verdict:
                    correct_count += 1
            except Exception as e:
                logging.error(f"Error in evaluate_citation_accuracy: {e}")
                
    return correct_count / total_citations if total_citations > 0 else 1.0
