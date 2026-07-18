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


class NVIDIACompatibilityEmbeddings(Embeddings):
    """Wrapper to support NVIDIA NIM embeddings (native 1536-dim via dimensions param) via OpenAI-compatible API."""
    def __init__(self, model: str, openai_api_key: str, base_url: str, dimensions: int = 1536):
        self.model = model
        self.api_key = openai_api_key
        self.base_url = base_url.rstrip("/")
        self.embedding_dim = dimensions  # Native dimension from API (no truncation needed)

    def _build_payload(self, texts: List[str], input_type: str = None) -> dict:
        """Build payload for NVIDIA embedding API."""
        payload = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float"
        }
        # nv-embed-v1: native 1536-dim, symmetric model - no dimensions param, no input_type
        return payload

    def _make_request(self, texts: List[str], input_type: str = None) -> List[List[float]]:
        """Make request to NVIDIA embedding API with proper format."""
        import httpx
        import time
        import re
        import random

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(texts, input_type)

        max_retries = 5
        last_error = None
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0, read=120.0), limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)) as client:
                    res = client.post(url, json=payload, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        embeddings = []
                        for item in data.get("data", []):
                            emb = item.get("embedding", [])
                            # Truncate to 1536 dimensions for pgvector compatibility (nv-embed-v1 returns 4096)
                            if len(emb) > 1536:
                                  emb = emb[:1536]
                            embeddings.append(emb)
                        return embeddings
                    elif res.status_code == 429:
                        raise httpx.HTTPStatusError("Rate Limit", request=res.request, response=res)
                    elif res.status_code >= 500:
                        raise Exception(f"Server error {res.status_code}: {res.text[:200]}")
                    else:
                        logging.warning(f"NVIDIA embedding returned {res.status_code}: {res.text[:200]}")
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
                    logging.warning(f"NVIDIA embedding rate limit. Sleeping {sleep_time:.1f}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(sleep_time)
                    continue
                elif is_transient:
                    sleep_time = random.uniform(0.5, 2.0)
                    logging.warning(f"NVIDIA embedding transient error: {e}. Retrying in {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                    continue
                else:
                    logging.error(f"NVIDIA embedding error: {e}")

        raise Exception(f"Failed to query NVIDIA embeddings after {max_retries} attempts. Last error: {last_error}")

    async def _make_request_async(self, texts: List[str], input_type: str = None) -> List[List[float]]:
        """Async version of _make_request."""
        import httpx
        import asyncio
        import re
        import random

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(texts, input_type)

        max_retries = 5
        last_error = None
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0, read=120.0), limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)) as client:
                    res = await client.post(url, json=payload, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        embeddings = []
                        for item in data.get("data", []):
                            emb = item.get("embedding", [])
                            # Truncate to 1536 dimensions for pgvector compatibility
                            if len(emb) > 1536:
                                emb = emb[:1536]
                            embeddings.append(emb)
                        return embeddings
                    elif res.status_code == 429:
                        raise httpx.HTTPStatusError("Rate Limit", request=res.request, response=res)
                    elif res.status_code >= 500:
                        raise Exception(f"Server error {res.status_code}: {res.text[:200]}")
                    else:
                        logging.warning(f"NVIDIA embedding async returned {res.status_code}: {res.text[:200]}")
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
                    logging.warning(f"NVIDIA embedding async rate limit. Sleeping {sleep_time:.1f}s (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(sleep_time)
                    continue
                elif is_transient:
                    sleep_time = random.uniform(0.5, 2.0)
                    logging.warning(f"NVIDIA embedding async transient error: {e}. Retrying in {sleep_time:.1f}s")
                    await asyncio.sleep(sleep_time)
                    continue
                else:
                    logging.error(f"NVIDIA embedding async error: {e}")

        raise Exception(f"Failed to query NVIDIA embeddings async after {max_retries} attempts. Last error: {last_error}")

    def embed_query(self, text: str) -> List[float]:
        return self._make_request([text])[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Process in smaller batches for NVIDIA API stability
        all_embeddings = []
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            all_embeddings.extend(self._make_request(batch))
        return all_embeddings

    async def aembed_query(self, text: str) -> List[float]:
        return (await self._make_request_async([text]))[0]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            all_embeddings.extend(await self._make_request_async(batch))
        return all_embeddings


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
        # Process texts in batches to reduce API calls
        all_embeddings = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            payload_parts = [{"text": text} for text in batch]
            payload = {
                "model": f"models/{self.model}",
                "content": {
                    "parts": payload_parts
                }
            }

            import httpx
            import re
            import random

            max_retries = 5
            last_error = None
            for attempt in range(max_retries):
                for api_version in ["v1beta", "v1"]:
                    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{self.model}:embedContent?key={self.api_key}"
                    try:
                        with httpx.Client(timeout=30.0) as client:
                            res = client.post(url, json=payload)
                            if res.status_code == 200:
                                data = res.json()
                                embeddings_data = data.get("embeddings", [])
                                if not embeddings_data and "embedding" in data:
                                    embeddings_data = [data["embedding"]]

                                for emb_data in embeddings_data:
                                    emb = emb_data["values"]
                                    padded_emb = self._pad(emb)
                                    all_embeddings.append(padded_emb)
                                break
                            elif res.status_code == 429:
                                raise httpx.HTTPStatusError("Rate Limit", request=res.request, response=res)
                            elif res.status_code >= 500:
                                raise Exception(f"Server error {res.status_code}: {res.text[:200]}")
                            else:
                                logging.warning(f"Embedding batch ({api_version}) returned {res.status_code}: {res.text[:200]}")
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
                            logging.warning(f"Embedding batch rate limit. Sleeping {sleep_time:.1f}s (attempt {attempt+1}/{max_retries})")
                            time.sleep(sleep_time)
                            break
                        elif is_transient:
                            sleep_time = random.uniform(0.5, 2.0)
                            logging.warning(f"Embedding batch transient error: {e}. Retrying in {sleep_time:.1f}s")
                            time.sleep(sleep_time)
                            break
                        else:
                            logging.error(f"Embedding batch error ({api_version}): {e}")
                else:
                    continue
                break
            else:
                raise Exception(f"Failed to query Gemini embeddings after {max_retries} attempts. Last error: {last_error}")

        return all_embeddings

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
        # Process texts in batches to reduce API calls
        all_embeddings = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            payload_parts = [{"text": text} for text in batch]
            payload = {
                "model": f"models/{self.model}",
                "content": {
                    "parts": payload_parts
                }
            }

            import httpx
            import asyncio
            import re
            import random

            max_retries = 5
            last_error = None
            for attempt in range(max_retries):
                for api_version in ["v1beta", "v1"]:
                    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{self.model}:embedContent?key={self.api_key}"
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            res = await client.post(url, json=payload)
                            if res.status_code == 200:
                                data = res.json()
                                embeddings_data = data.get("embeddings", [])
                                if not embeddings_data and "embedding" in data:
                                    embeddings_data = [data["embedding"]]

                                for emb_data in embeddings_data:
                                    emb = emb_data["values"]
                                    padded_emb = self._pad(emb)
                                    all_embeddings.append(padded_emb)
                                break
                            elif res.status_code == 429:
                                raise httpx.HTTPStatusError("Rate Limit", request=res.request, response=res)
                            elif res.status_code >= 500:
                                raise Exception(f"Server error {res.status_code}: {res.text[:200]}")
                            else:
                                logging.warning(f"Embedding async batch ({api_version}) returned {res.status_code}: {res.text[:200]}")
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
                            logging.warning(f"Embedding async batch rate limit. Sleeping {sleep_time:.1f}s (attempt {attempt+1}/{max_retries})")
                            await asyncio.sleep(sleep_time)
                            break
                        elif is_transient:
                            sleep_time = random.uniform(0.5, 2.0)
                            logging.warning(f"Embedding async batch transient error: {e}. Retrying in {sleep_time:.1f}s")
                            await asyncio.sleep(sleep_time)
                            break
                        else:
                            logging.error(f"Embedding async batch error ({api_version}): {e}")
                else:
                    continue
                break
            else:
                raise Exception(f"Failed to query Gemini embeddings async after {max_retries} attempts. Last error: {last_error}")

        return all_embeddings


def _is_gemini_base_url(base_url: str | None) -> bool:
    """Check if base_url points to Google Gemini API."""
    if not base_url:
        return False
    return "generativelanguage.googleapis.com" in base_url


def _is_nvidia_base_url(base_url: str | None) -> bool:
    """Check if base_url points to NVIDIA NIM API."""
    if not base_url:
        return False
    return "integrate.api.nvidia.com" in base_url


def _build_embeddings_model(model: str, api_key: str, base_url: str | None) -> Embeddings:
    """Factory to create the appropriate embeddings model based on API endpoint."""
    if _is_gemini_base_url(base_url):
        logging.info(f"Using Gemini embeddings: {model} (will pad to 1536 dims)")
        return GeminiCompatibilityEmbeddings(model=model, openai_api_key=api_key)
    elif _is_nvidia_base_url(base_url):
        import os
        dimensions = int(os.environ.get("EMBEDDING_DIMENSIONS", "1536"))
        logging.info(f"Using NVIDIA NIM embeddings: {model} (native {dimensions} dims via dimensions param)")
        return NVIDIACompatibilityEmbeddings(model=model, openai_api_key=api_key, base_url=base_url, dimensions=dimensions)
    else:
        # Use LangChain's OpenAIEmbeddings for other OpenAI-compatible APIs
        logging.info(f"Using OpenAI-compatible embeddings: {model} at {base_url}")
        return OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            base_url=base_url,
            timeout=60.0,
            max_retries=3,
        )


def get_embeddings_model() -> Embeddings:
    global _embeddings_model
    if _embeddings_model is None:
        # Read from EMBEDDING_* env vars with fallback to settings
        import os
        from app.config import settings

        api_key = os.environ.get("EMBEDDING_OPENAI_API_KEY", settings.openai_api_key)
        base_url = os.environ.get("EMBEDDING_OPENAI_API_BASE", settings.openai_api_base)
        model_name = os.environ.get("EMBEDDING_OPENAI_MODEL_NAME", settings.embedding_model_name)

        if (api_key != settings.openai_api_key
                or base_url != settings.openai_api_base
                or model_name != settings.embedding_model_name):
            logging.info(
                "Embedding model override active → model=%s, base=%s, key_set=%s",
                model_name, base_url, bool(api_key)
            )

        _embeddings_model = _build_embeddings_model(model_name, api_key, base_url)
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
    """Compute text embeddings in small batches for NVIDIA API stability."""
    embeddings_model = get_embeddings_model()
    results = []
    for i in range(0, len(texts), 25):
        batch = texts[i:i+25]
        results.extend(embeddings_model.embed_documents(batch))
    return results


async def aembed_text_batch(texts: List[str], max_concurrent: int = 3) -> List[List[float]]:
    """Async batched embedding with controlled concurrency for NVIDIA API."""
    import asyncio
    embeddings_model = get_embeddings_model()

    # Check if model supports async
    if not hasattr(embeddings_model, "aembed_documents"):
        # Fallback to sync
        return embed_text_batch(texts)

    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_batch(batch: List[str]) -> List[List[float]]:
        async with semaphore:
            return await embeddings_model.aembed_documents(batch)

    # Create tasks for all batches
    tasks = []
    for i in range(0, len(texts), 25):
        batch = texts[i:i+25]
        tasks.append(process_batch(batch))

    # Run concurrently with semaphore limiting
    batch_results = await asyncio.gather(*tasks)

    # Flatten results
    results = []
    for batch_emb in batch_results:
        results.extend(batch_emb)
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
    """Generate technical caption for a figure using vision model with 429 rate limit retries."""
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
                    f"Vision API rate limit (429) hit during image captioning. "
                    f"Sleeping for {sleep_time:.2f}s before retry {attempt + 1}/{max_retries}..."
                )
                await asyncio.sleep(sleep_time)
            else:
                logging.error(f"Non-rate-limit exception in caption_image: {e}")
                raise e

    raise Exception("Max retries exceeded for vision image captioning due to rate limits.")