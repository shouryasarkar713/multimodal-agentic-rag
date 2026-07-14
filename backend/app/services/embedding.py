import time
import torch
import open_clip
from PIL import Image
from typing import List
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage
from app.config import settings
from app.utils.image_utils import resize_and_encode_image

# Singleton instances for lazy loading
_embeddings_model = None
_clip_model = None
_clip_preprocess = None
_vision_model = None

# Rate limiter tracker (max 5 calls/sec = 0.2s spacing)
_last_call_time = 0.0

import logging
from langchain_core.embeddings import Embeddings

class GeminiCompatibilityEmbeddings(Embeddings):
    """Wrapper to support Google Gemini native embeddings with zero-padding to 1536 dimensions."""
    def __init__(self, model: str, openai_api_key: str):
        self.model = model
        self.api_key = openai_api_key
        
    def _pad(self, vec: List[float]) -> List[float]:
        # Google text-embedding-004 outputs 768 dimensions. Pad to 1536.
        if len(vec) < 1536:
            vec = vec + [0.0] * (1536 - len(vec))
        return vec[:1536]
        
    def embed_query(self, text: str) -> List[float]:
        import httpx
        import time
        import re
        import random
        
        max_retries = 5
        last_error = None
        for attempt in range(max_retries):
            for api_version in ["v1beta", "v1"]:
                url = f"https://generativelanguage.googleapis.com/{api_version}/models/{self.model}:embedContent?key={self.api_key}"
                payload = {
                    "model": f"models/{self.model}",
                    "content": {
                        "parts": [{"text": text}]
                    }
                }
                try:
                    with httpx.Client(timeout=30.0) as client:
                        res = client.post(url, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            emb = data["embedding"]["values"]
                            return self._pad(emb)
                        elif res.status_code == 429:
                            raise httpx.HTTPStatusError("Rate Limit", request=res.request, response=res)
                        elif res.status_code >= 500:
                            raise Exception(f"Server error {res.status_code}: {res.text[:200]}")
                        else:
                            logging.warning(f"Gemini embedding ({api_version}) returned {res.status_code}: {res.text[:200]}")
                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    is_rate_limit = "429" in err_str or "rate limit" in err_str or "resource_exhausted" in err_str
                    is_transient = "disconnect" in err_str or "ssl" in err_str or "eof" in err_str or "timeout" in err_str or "server error" in err_str or "connection" in err_str
                    
                    if is_rate_limit:
                        sleep_time = min((2 ** attempt) + random.uniform(0.5, 1.5) + 2, 30)
                        match = re.search(r'retry in ([\d\.]+)s', str(e))
                        if match:
                            sleep_time = float(match.group(1)) + 1
                        logging.warning(f"Embedding rate limit. Sleeping {sleep_time:.1f}s (attempt {attempt+1}/{max_retries})")
                        time.sleep(sleep_time)
                        break
                    elif is_transient:
                        sleep_time = random.uniform(0.5, 2.0)
                        logging.warning(f"Embedding transient error: {e}. Retrying in {sleep_time:.1f}s")
                        time.sleep(sleep_time)
                        break
                    else:
                        logging.error(f"Embedding error ({api_version}): {e}")
                        
        raise Exception(f"Failed to query Gemini embeddings after {max_retries} attempts. Last error: {last_error}")
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(t) for t in texts]
        
    async def aembed_query(self, text: str) -> List[float]:
        import httpx
        import asyncio
        import re
        import random
        
        max_retries = 5
        last_error = None
        for attempt in range(max_retries):
            for api_version in ["v1beta", "v1"]:
                url = f"https://generativelanguage.googleapis.com/{api_version}/models/{self.model}:embedContent?key={self.api_key}"
                payload = {
                    "model": f"models/{self.model}",
                    "content": {
                        "parts": [{"text": text}]
                    }
                }
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        res = await client.post(url, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            emb = data["embedding"]["values"]
                            return self._pad(emb)
                        elif res.status_code == 429:
                            raise httpx.HTTPStatusError("Rate Limit", request=res.request, response=res)
                        elif res.status_code >= 500:
                            raise Exception(f"Server error {res.status_code}: {res.text[:200]}")
                        else:
                            logging.warning(f"Embedding async ({api_version}) returned {res.status_code}: {res.text[:200]}")
                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    is_rate_limit = "429" in err_str or "rate limit" in err_str or "resource_exhausted" in err_str
                    is_transient = "disconnect" in err_str or "ssl" in err_str or "eof" in err_str or "timeout" in err_str or "server error" in err_str or "connection" in err_str
                    
                    if is_rate_limit:
                        sleep_time = min((2 ** attempt) + random.uniform(0.5, 1.5) + 2, 30)
                        match = re.search(r'retry in ([\d\.]+)s', str(e))
                        if match:
                            sleep_time = float(match.group(1)) + 1
                        logging.warning(f"Embedding async rate limit. Sleeping {sleep_time:.1f}s (attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(sleep_time)
                        break
                    elif is_transient:
                        sleep_time = random.uniform(0.5, 2.0)
                        logging.warning(f"Embedding async transient error: {e}. Retrying in {sleep_time:.1f}s")
                        await asyncio.sleep(sleep_time)
                        break
                    else:
                        logging.error(f"Embedding async error ({api_version}): {e}")
                        
        raise Exception(f"Failed to query Gemini embeddings async after {max_retries} attempts. Last error: {last_error}")
        
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        import asyncio
        tasks = [self.aembed_query(t) for t in texts]
        return await asyncio.gather(*tasks)

def get_embeddings_model():
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = GeminiCompatibilityEmbeddings(
            model=settings.embedding_model_name,
            openai_api_key=settings.openai_api_key
        )
    return _embeddings_model

def get_clip_model():
    global _clip_model, _clip_preprocess
    if _clip_model is None:
        # Load CLIP ViT-B-32 on CPU
        model, _, preprocess = open_clip.create_model_and_transforms(
            settings.clip_model_name,
            pretrained=settings.clip_pretrained,
            device="cpu"
        )
        model.eval()
        _clip_model = model
        _clip_preprocess = preprocess
    return _clip_model, _clip_preprocess

def get_vision_model():
    global _vision_model
    if _vision_model is None:
        _vision_model = ChatOpenAI(
            model=settings.openai_model_name,
            openai_api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            max_tokens=150
        )
    return _vision_model

def enforce_rate_limit():
    """Ensure at least 4.5s spacing between Vision API calls to respect 15 RPM free tier limits."""
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < 4.5:
        time.sleep(4.5 - elapsed)
    _last_call_time = time.time()

def embed_text_batch(texts: List[str]) -> List[List[float]]:
    """Compute text embeddings in batches of 100."""
    embeddings_model = get_embeddings_model()
    results = []
    for i in range(0, len(texts), 100):
        batch = texts[i:i+100]
        results.extend(embeddings_model.embed_documents(batch))
    return results

def embed_image(image_path: str) -> List[float]:
    """Compute 512-dim normalized CLIP embedding for a figure on CPU."""
    model, preprocess = get_clip_model()
    img = Image.open(image_path)
    img_input = preprocess(img).unsqueeze(0)
    
    with torch.no_grad():
        image_features = model.encode_image(img_input)
        # Normalize to unit sphere for cosine similarity
        image_features /= image_features.norm(dim=-1, keepdim=True)
        vector = image_features[0].cpu().numpy().tolist()
        
    return vector

async def caption_image(image_path: str, context: str) -> str:
    """Generate technical caption for a figure using Gemini vision with 429 rate limit retries."""
    enforce_rate_limit()
    
    # Base64 encode and resize figure to max 512px
    base64_image = resize_and_encode_image(image_path, max_size=512)
    
    prompt = (
        "Describe this figure from a technical research paper in 2-3 sentences. "
        "Focus on what data or architecture it shows, any axis labels, and key takeaways."
    )
    if context:
        prompt += f"\n\nSurrounding text context:\n{context}"
        
    model = get_vision_model()
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            }
        ]
    )
    
    import asyncio
    import re
    import random
    
    max_retries = 6
    for attempt in range(max_retries):
        try:
            response = await model.ainvoke([message])
            return response.content.strip()
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str or "resource_exhausted" in err_str:
                sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5) + 5
                match = re.search(r'retry in ([\d\.]+)s', str(e))
                if match:
                    sleep_time = float(match.group(1)) + 1
                
                logging.warning(
                    f"Gemini API rate limit (429) hit during image captioning. "
                    f"Sleeping for {sleep_time:.2f}s before retry {attempt + 1}/{max_retries}..."
                )
                await asyncio.sleep(sleep_time)
            else:
                logging.error(f"Non-rate-limit exception in caption_image: {e}")
                raise e
                
    raise Exception("Max retries exceeded for Gemini image captioning due to rate limits.")
