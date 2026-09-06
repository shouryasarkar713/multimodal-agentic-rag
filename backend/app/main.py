import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

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


@app.on_event("startup")
async def startup_db_init():
    try:
        from app.dependencies import engine
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS document_ids JSONB DEFAULT '[]'::jsonb;"))
            logging.info("Schema check completed: sessions.document_ids column verified.")
    except Exception as e:
        logging.warning("Could not auto-apply sessions.document_ids schema check: %s", e)
