from typing import AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from .llm_interface import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = ChatGoogleGenerativeAI(google_api_key=api_key, model=model)
        self.model = model

    async def generate(self, prompt: str, chat_history: list = []) -> str:
        messages = chat_history + [{"role": "user", "content": prompt}]
        response = await self.client.ainvoke(messages)
        return response.content

    async def generate_stream(
        self, prompt: str, chat_history: list = []
    ) -> AsyncGenerator[str, None]:
        messages = chat_history + [{"role": "user", "content": prompt}]
        async for chunk in self.client.astream(messages):
            if chunk.content:
                content = chunk.content
                if isinstance(content, dict):
                    content = content.get("text", str(content))
                elif isinstance(content, list):
                    content = "".join(
                        item.get("text", str(item))
                        if isinstance(item, dict)
                        else str(item)
                        for item in content
                    )
                yield content


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = ChatOpenAI(api_key=api_key, model=model)
        self.model = model

    async def generate(self, prompt: str, chat_history: list = []) -> str:
        chat_history.append(self.construct_prompt(prompt, "user"))
        response = await self.client.ainvoke(chat_history)
        return response.content

    async def generate_stream(
        self, prompt: str, chat_history: list = []
    ) -> AsyncGenerator[str, None]:
        messages = chat_history + [{"role": "user", "content": prompt}]
        async for chunk in self.client.astream(messages):
            if chunk.content:
                content = chunk.content
                if isinstance(content, list):
                    content = "".join(str(item) for item in content)
                yield content


class DeepSeekProvider(OpenAIProvider):
    def __init__(self, api_key: str, model: str):
        self.client = ChatOpenAI(
            api_key=api_key, base_url="https://openrouter.ai/api/v1", model=model
        )
        self.model = model
