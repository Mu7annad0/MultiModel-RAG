from typing import List, Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    COHERE_API_KEY: str
    DEEPSEEK_API_KEY: str

    OPENAI_EMBEDDING_MODEL: str
    GEMINI_EMBEDDING_MODEL: str
    COHERE_EMBEDDING_MODEL: str

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

    DB_DIR: str

    class Config:
        env_file = ".env"


def load_settings():
    return Settings()
