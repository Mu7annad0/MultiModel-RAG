from typing import Dict, Generator
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """Abstract interface for an LLM provider."""

    @abstractmethod
    def generate(self, prompt: str, chat_history: list=[]) -> str:
        """Generate a response to the given prompt."""
        pass
    
    @abstractmethod
    def generate_stream(self, prompt: str, chat_history: list=[]) -> Generator[str, None, None]:
        """Generate a response to the given prompt."""
        pass
    
    @staticmethod
    def construct_prompt(query: str, role: str) -> Dict[str, str]:
        return {"role": role, "content": query}