from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    FILE_PAGES: int
    FILE_FORMATS: List[str]
    FILE_CHUNK_SIZE: int

    class Config:
        env_file = ".env"


def load_settings():
    return Settings()