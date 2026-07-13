from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator
from app.config import settings

# Create async database engine
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False
)

# Async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """Dependency to verify X-API-Key header against config.
    Returns 401 instead of 422 if header is missing.
    """
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key
