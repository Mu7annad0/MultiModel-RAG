from typing import AsyncGenerator
import asyncio
from google import genai
from openai import AsyncOpenAI

from .llm_interface import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _prepare_history(self, prompt: str, chat_history: list):
        gemini_history = []
        for msg in chat_history:
            if msg["role"] != "system":
                role = "model" if msg["role"] == "assistant" else "user"
                gemini_history.append(
                    {"role": role, "parts": [{"text": msg["content"]}]}
                )

        gemini_history.append({"role": "user", "parts": [{"text": prompt}]})
        return gemini_history

    async def generate(self, prompt: str, chat_history: list = []) -> str:
        history = self._prepare_history(prompt, chat_history)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model, contents=history
            ),
        )
        return response.text or ""

    async def generate_stream(
        self, prompt: str, chat_history: list = []
    ) -> AsyncGenerator[str, None]:
        history = self._prepare_history(prompt, chat_history)
        loop = asyncio.get_event_loop()
        stream = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content_stream(
                model=self.model, contents=history
            ),
        )
        for chunk in stream:
            if chunk.text:
                yield chunk.text


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, prompt: str, chat_history: list = []) -> str:
        chat_history.append(self.construct_prompt(prompt, "user"))
        response = await self.client.chat.completions.create(
            model=self.model, messages=chat_history
        )
        return response.choices[0].message.content or ""

    async def generate_stream(
        self, prompt: str, chat_history: list = []
    ) -> AsyncGenerator[str, None]:
        messages = chat_history + [{"role": "user", "content": prompt}]
        response = await self.client.chat.completions.create(
            model=self.model, messages=messages, stream=True
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class DeepSeekProvider(OpenAIProvider):
    def __init__(self, api_key: str, model: str):
        self.client = AsyncOpenAI(
            api_key=api_key, base_url="https://openrouter.ai/api/v1"
        )
        self.model = model
