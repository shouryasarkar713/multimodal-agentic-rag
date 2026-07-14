import re
import json
import logging
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import settings

def get_eval_llm():
    return ChatOpenAI(
        model=settings.openai_model_name,
        openai_api_key=settings.openai_api_key,
        openai_api_base=settings.openai_api_base,
        temperature=0.0
    )

def get_eval_embeddings():
    from app.services.embedding import get_embeddings_model
    return get_embeddings_model()

async def evaluate_faithfulness(answer: str, context_chunks: List[str]) -> float:
    """
    Check if the claims in the generated answer are supported by the retrieved context.
    Faithfulness = (number of supported claims) / (total claims in the answer).
    """
    if not answer or not context_chunks:
        return 1.0
        
    llm = get_eval_llm()
    
    # Step 1: Extract claims from the generated answer
    extract_prompt = (
        f"Answer to analyze:\n{answer}\n\n"
        "Extract all individual factual claims made in the answer above. "
        "Return them as a JSON list of strings under the key 'claims'. Output ONLY valid JSON."
    )
    
    try:
        response = await llm.ainvoke(extract_prompt)
        # Handle code fence formatting in LLM output
        clean_text = re.sub(r"```json\s*|\s*```", "", response.content.strip())
        claims = json.loads(clean_text).get("claims", [])
    except Exception as e:
        logging.error(f"Error extracting claims: {e}")
        return 0.5  # Fallback score if parser fails
        
    if not claims:
        return 1.0
        
    # Step 2: Check each claim against the context
    context_str = "\n---\n".join(context_chunks)
    grade_prompt = (
        f"Context:\n{context_str}\n\n"
        f"Claims to verify:\n{json.dumps(claims)}\n\n"
        "For each claim, determine if it is directly supported or logically inferred by the context. "
        "Return a JSON list of booleans (true for supported, false for unsupported) under the key 'supported'. "
        "Output ONLY valid JSON. The length of the boolean list MUST match the number of claims."
    )
    
    try:
        response = await llm.ainvoke(grade_prompt)
        clean_text = re.sub(r"```json\s*|\s*```", "", response.content.strip())
        supported = json.loads(clean_text).get("supported", [])
        
        if len(supported) != len(claims):
            # Fallback if size mismatch
            supported = supported[:len(claims)] + [False] * max(0, len(claims) - len(supported))
            
        supported_count = sum(1 for val in supported if val is True)
        return supported_count / len(claims)
    except Exception as e:
        logging.error(f"Error grading claims: {e}")
        return 0.5
        
async def evaluate_answer_relevancy(query: str, answer: str) -> float:
    """
    Measure semantic similarity between the query and generated answer using embeddings.
    """
    if not answer:
        return 0.0
        
    try:
        import numpy as np
        emb_model = get_eval_embeddings()
        
        # embed both query and answer
        vectors = await emb_model.aembed_documents([query, answer])
        v1, v2 = np.array(vectors[0]), np.array(vectors[1])
        
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
            
        cosine_sim = dot_product / (norm_v1 * norm_v2)
        # Cosine similarity is usually in [-1, 1], scale or clip to [0, 1]
        return float(max(0.0, cosine_sim))
    except Exception as e:
        logging.error(f"Error calculating answer relevancy: {e}")
        return 0.5

async def evaluate_context_precision(query: str, retrieved_chunks: List[str], gold_relevant_chunks: List[str]) -> float:
    """
    Evaluate if relevant chunks are ranked higher in the retrieved chunks.
    Mean Average Precision (MAP) style formula.
    """
    if not retrieved_chunks or not gold_relevant_chunks:
        return 0.0
        
    llm = get_eval_llm()
    
    # Grade relevance of each retrieved chunk using LLM
    relevance_scores = []
    for chunk in retrieved_chunks:
        grade_prompt = (
            f"Query: {query}\n\n"
            f"Chunk content: {chunk}\n\n"
            "Does this chunk contain information that directly helps answer the query? "
            "Respond with 'YES' or 'NO' and nothing else."
        )
        try:
            res = await llm.ainvoke(grade_prompt)
            clean_res = res.content.strip().upper()
            relevance_scores.append(1 if "YES" in clean_res else 0)
        except Exception as e:
            logging.error(f"Error grading chunk relevance: {e}")
            relevance_scores.append(0)
            
    # Calculate precision at K
    precision_at_k = []
    relevant_found = 0
    
    for k, score in enumerate(relevance_scores):
        if score == 1:
            relevant_found += 1
            precision_at_k.append(relevant_found / (k + 1))
            
    if not precision_at_k:
        return 0.0
        
    return sum(precision_at_k) / len(precision_at_k)

async def evaluate_citation_accuracy(answer: str, retrieved_chunks: List[str]) -> float:
    """
    Verify that every citation [N] matches text from chunk indices, and
    every citation claim matches the context of the cited chunk.
    Citation Accuracy = (correctly cited claims) / (total cited claims).
    """
    # Find all citations in format [N]
    inline_cits = re.findall(r'\[(\d+)\]', answer)
    if not inline_cits:
        # If no citations were needed or made, default to 1.0 (unless sources are completely un-cited)
        return 1.0
        
    llm = get_eval_llm()
    
    # Map citations to their actual sentences
    # Split answer by sentences
    sentences = re.split(r'(?<=[.!?])\s+', answer)
    cited_sentences = []
    for sent in sentences:
        match = re.search(r'\[(\d+)\]', sent)
        if match:
            idx = int(match.group(1)) - 1 # 1-based index to 0-based
            # Clean citations from sentence text
            clean_sent = re.sub(r'\[\d+\]', '', sent).strip()
            cited_sentences.append((clean_sent, idx))
            
    if not cited_sentences:
        return 1.0
        
    correct_citations = 0
    for sent, chunk_idx in cited_sentences:
        if chunk_idx < 0 or chunk_idx >= len(retrieved_chunks):
            # Invalid/hallucinated chunk index
            continue
            
        cited_chunk = retrieved_chunks[chunk_idx]
        grade_prompt = (
            f"Cited Statement: {sent}\n\n"
            f"Source Document Paragraph: {cited_chunk}\n\n"
            "Does the Source Document Paragraph directly support the claim made in the Cited Statement? "
            "Respond with 'YES' or 'NO' and nothing else."
        )
        try:
            res = await llm.ainvoke(grade_prompt)
            if "YES" in res.content.strip().upper():
                correct_citations += 1
        except Exception as e:
            logging.error(f"Error grading citation: {e}")
            
    return correct_citations / len(cited_sentences)
