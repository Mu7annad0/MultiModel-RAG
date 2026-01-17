from typing import Dict, AsyncGenerator
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface for an LLM provider."""

    @abstractmethod
    async def generate(self, prompt: str, chat_history: list = []) -> str:
        """Generate a response to the given prompt."""
        pass

    @abstractmethod
    async def generate_stream(
        self, prompt: str, chat_history: list = []
    ) -> AsyncGenerator[str, None]:
        """Generate a response to the given prompt."""
        pass

    @staticmethod
    def construct_prompt(query: str, role: str) -> Dict[str, str]:
        return {"role": role, "content": query}
