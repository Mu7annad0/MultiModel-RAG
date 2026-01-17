import json
import logging
from typing import Optional, List, Dict, Union
from openai import AsyncOpenAI

from .llm_providers import GeminiProvider, OpenAIProvider, DeepSeekProvider


class GenerationClient:
    def __init__(self, settings: dict, provider: Optional[str] = "openai"):
        self.settings = settings
        self.provider: Optional[
            Union[OpenAIProvider, GeminiProvider, DeepSeekProvider]
        ] = None
        self.logger = logging.getLogger(__name__)
        self.set_model(provider or "openai")

    def set_model(
        self,
        provider: str,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        provider = provider.lower()

        if provider == "openai":
            model_id = model_id or getattr(
                self.settings, "OPENAI_MODEL_ID", "gpt-5-mini"
            )
            api_key = api_key or getattr(self.settings, "OPENAI_API_KEY", None)
            self.provider = OpenAIProvider(api_key=api_key, model=model_id)

        elif provider == "gemini":
            model_id = model_id or getattr(
                self.settings, "GEMINI_MODEL_ID", "gemini-3-flash-preview"
            )
            api_key = api_key or getattr(self.settings, "GEMINI_API_KEY", None)
            self.provider = GeminiProvider(api_key=api_key, model=model_id)

        elif provider == "deepseek":
            model_id = model_id or getattr(
                self.settings, "DEEPSEEK_MODEL_ID", "deepseek/deepseek-r1-0528:free"
            )
            api_key = api_key or getattr(self.settings, "DEEPSEEK_API_KEY", None)
            self.provider = DeepSeekProvider(api_key=api_key, model=model_id)

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def answer(
        self, prompt: str, chat_history: Optional[List[Dict]] = None
    ) -> str:
        if self.provider is None:
            raise RuntimeError("Provider not set. Call set_model() first.")
        self.logger.info(f"Generating answer for prompt with {self.provider.model}")
        return await self.provider.generate(prompt, chat_history or [])

    async def answer_stream(
        self, prompt: str, chat_history: Optional[List[Dict]] = None
    ):
        if self.provider is None:
            raise RuntimeError("Provider not set.")
        self.logger.info(f"Generating answer for prompt with {self.provider.model}")
        return self.provider.generate_stream(prompt, chat_history or [])

    @staticmethod
    def construct_prompt(query: str, role: str) -> Dict[str, str]:
        return {"role": role, "content": query}


class AdvancedRAGClient:
    def __init__(self, settings):
        self.settings = settings
        self.client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)

    async def filter_chunks(self, prompt, question: str, chunks: List[str]) -> List[int]:
        formatted_chunks = "\n".join(
            f"Chunk {i}: {chunk.text}" for i, chunk in enumerate(chunks)
        )

        filter_prompt = prompt.substitute(
            question=question,
            chunks=formatted_chunks,
        )

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": filter_prompt}],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        try:
            parsed = json.loads(content)
            return parsed.get("relevant_chunk_indices", [])
        except json.JSONDecodeError:
            return []

    async def split_query(self, prompt, query: str) -> list:
        split_prompt = prompt.substitute(
            question=query,
        )
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": split_prompt}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        try:
            parsed = json.loads(content)
            return parsed.get("decomposed_questions", [])
        except json.JSONDecodeError:
            return []
