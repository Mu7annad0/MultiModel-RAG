from typing import List, Literal
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    document_id: str
    query: str
    provider: Literal["openai", "gemini", "deepseek"]
    generate_audio: bool


def get_default_db_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, "assets", "database", "qdrant_db")


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    COHERE_API_KEY: str
    DEEPSEEK_API_KEY: str

    OPENAI_EMBEDDING_MODEL: str
    GEMINI_EMBEDDING_MODEL: str
    COHERE_EMBEDDING_MODEL: str

    EVALUATION_MODEL: str

    OPENAI_MODEL_ID: str
    GEMINI_MODEL_ID: str
    DEEPSEEK_MODEL_ID: str

    EMBEDDING_PROVIDER: Literal["openai", "gemini", "cohere"]
    EMBEDDING_DIMENSION: int

    FILTER: bool
    SPLIT: bool

    STREAMING: bool

    FILE_PAGES: int
    FILE_FORMATS: List[str]
    FILE_CHUNK_SIZE: int

    CHUNK_OVERLAP: int
    CHUNK_SIZE: int

    DB_DIR: str = Field(default_factory=get_default_db_dir)

    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        )
    )


def load_settings():
    return Settings()
