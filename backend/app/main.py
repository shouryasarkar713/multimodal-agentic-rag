from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router

app = FastAPI(
    title="Multimodal Technical Research Assistant API",
    description="Backend API for Agentic RAG and document query",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router with /api prefix
app.include_router(api_router, prefix="/api")

# Health check endpoint
@app.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
