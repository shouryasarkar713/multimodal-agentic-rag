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
    openai_model_name: str = Field(default="gpt-4o", alias="OPENAI_MODEL_NAME")
    embedding_model_name: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL_NAME")
    
    # Model configs from tech stack
    clip_model_name: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"
    cross_encoder_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

settings = Settings()
