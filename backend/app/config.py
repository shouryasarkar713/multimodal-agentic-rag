from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    database_url: str = Field(alias="DATABASE_URL")
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    api_key: str = Field(alias="API_KEY")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="research-assistant", alias="LANGSMITH_PROJECT")
    data_dir: str = Field(default="/data", alias="DATA_DIR")
    openai_model_name: str = Field(default="gemini-1.5-flash", alias="OPENAI_MODEL_NAME")
    embedding_model_name: str = Field(default="text-embedding-004", alias="EMBEDDING_MODEL_NAME")
    openai_api_base: str | None = Field(default="https://generativelanguage.googleapis.com/v1beta/openai", alias="OPENAI_API_BASE")
    
    # Model configs from tech stack
    clip_model_name: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"
    cross_encoder_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

import os

settings = Settings()

# Fallback to Google API keys if OpenAI key is missing or placeholder
if settings.openai_api_key == "sk-placeholder-key" or not settings.openai_api_key:
    for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        val = os.environ.get(var)
        if val:
            settings.openai_api_key = val
            break

# Inject OpenAI compatibility endpoint for Gemini API
if settings.openai_api_base:
    os.environ["OPENAI_API_BASE"] = settings.openai_api_base
    os.environ["OPENAI_BASE_URL"] = settings.openai_api_base
