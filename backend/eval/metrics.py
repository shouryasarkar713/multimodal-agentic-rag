import os
import re
import json
import logging
from typing import List, Dict, Any
from langchain_openai import OpenAIEmbeddings

from app.agents.llm_factory import get_generation_llm
from app.config import settings
from app.services.embedding import get_embeddings_model

def get_eval_llm():
    """Use the shared generation LLM factory (reads LLM_OPENAI_* env vars).
    Falls back to EVAL_* env vars for backwards compatibility, then to main settings.
    """
    from app.config import settings

    # Check for EVAL-specific env vars (backwards compat), then LLM_* vars,
    # then fall back to main settings
    api_key = (os.environ.get("EVAL_OPENAI_API_KEY") or
               os.environ.get("LLM_OPENAI_API_KEY") or
               settings.openai_api_key)
    base_url = (os.environ.get("EVAL_OPENAI_API_BASE") or
                os.environ.get("LLM_OPENAI_API_BASE") or
                settings.openai_api_base)
    model_name = (os.environ.get("EVAL_OPENAI_MODEL_NAME") or
                  os.environ.get("LLM_OPENAI_MODEL_NAME") or
                  settings.openai_model_name)

    # Optional: Log when using eval-specific or LLM-specific settings
    if (api_key != settings.openai_api_key or
        base_url != settings.openai_api_base or
        model_name != settings.openai_model_name):
        logging.info(f"Using evaluation LLM: {model_name} at {base_url}")

    return get_generation_llm()

def get_eval_embeddings():
    from app.services.embedding import get_embeddings_model
    return get_embeddings_model()

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
    Calculate semantic similarity between user question and LLM-generated potential questions.
    Relevancy = Mean( CosineSimilarity(Embedding(GeneratedQuestion_i), Embedding(UserQuestion)) )
    """
    import numpy as np
    if not answer.strip():
        return 0.0

    llm = get_eval_llm()
    embeddings_model = get_eval_embeddings()

    # Step 1: Ask LLM to generate 3 search-like questions that the generated answer could resolve
    prompt = f"""
    Given the following generated answer, write exactly three distinct search queries or questions that this answer directly resolves.
    Write each question on a new line. Do not write numbers, bullet points, introductory text, or any extra characters.
    
    Answer:
    {answer}
    """
    try:
        res = await llm.ainvoke(prompt)
        lines = res.content.strip().split("\n")
        # Filter empty lines
        generated_questions = [l.strip() for l in lines if l.strip()]
        # Take first 3
        generated_questions = generated_questions[:3]
        
        if not generated_questions:
            return 0.0

        # Step 2: Embed the original question and the 3 generated questions
        q_emb = await embeddings_model.aembed_query(question)
        v_q = np.array(q_emb)
        norm_q = np.linalg.norm(v_q)
        if norm_q == 0:
            return 0.0
            
        similarities = []
        for gq in generated_questions:
            g_emb = await embeddings_model.aembed_query(gq)
            v_g = np.array(g_emb)
            norm_g = np.linalg.norm(v_g)
            if norm_g == 0:
                continue
            cos_sim = np.dot(v_q, v_g) / (norm_q * norm_g)
            similarities.append(float(cos_sim))

        return sum(similarities) / len(similarities) if similarities else 0.0
    except Exception as e:
        logging.error(f"Error in evaluate_answer_relevancy: {e}")
        return 0.0

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
