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

from langchain_core.embeddings import Embeddings

class GeminiCompatibilityEmbeddings(Embeddings):
    """Wrapper to support Google Gemini compatibility layer embeddings with zero-padding to 1536 dimensions."""
    def __init__(self, model: str, openai_api_key: str):
        self.embeddings = OpenAIEmbeddings(
            model=model,
            openai_api_key=openai_api_key,
            openai_api_base=settings.openai_api_base
        )
        
    def _pad(self, vec: List[float]) -> List[float]:
        # Google text-embedding-004 outputs 768 dimensions. Pad to 1536.
        if len(vec) < 1536:
            vec = vec + [0.0] * (1536 - len(vec))
        return vec[:1536]
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embs = self.embeddings.embed_documents(texts)
        return [self._pad(e) for e in embs]
        
    def embed_query(self, text: str) -> List[float]:
        emb = self.embeddings.embed_query(text)
        return self._pad(emb)
        
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        embs = await self.embeddings.aembed_documents(texts)
        return [self._pad(e) for e in embs]
        
    async def aembed_query(self, text: str) -> List[float]:
        emb = await self.embeddings.aembed_query(text)
        return self._pad(emb)

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
            openai_api_base=settings.openai_api_base,
            max_tokens=150
        )
    return _vision_model

def enforce_rate_limit():
    """Ensure at least 200ms spacing between Vision API calls."""
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < 0.2:
        time.sleep(0.2 - elapsed)
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

def caption_image(image_path: str, context: str) -> str:
    """Generate technical caption for a figure using GPT-4.1 vision."""
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
    
    response = model.invoke([message])
    return response.content.strip()
