from typing import Generator
from google import genai
from openai import OpenAI

from .llm_interface import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model
    
    def _prepare_history(self, prompt: str, chat_history: list):
        gemini_history = []
        for msg in chat_history:
            if msg['role'] != 'system':
                role = "model" if msg['role'] == "assistant" else "user"
                gemini_history.append({"role": role, "parts": [{"text": msg['content']}]})
        
        gemini_history.append({"role": "user", "parts": [{"text": prompt}]})
        return gemini_history

    def generate(self, prompt: str, chat_history: list=[]) -> str:
        history = self._prepare_history(prompt, chat_history)
        response = self.client.models.generate_content(model=self.model, contents=history)
        return response.text
    
    def generate_stream(self, prompt: str, chat_history: list=[]) -> Generator[str, None, None]:
        history = self._prepare_history(prompt, chat_history)
        for chunk in self.client.models.generate_content_stream(model=self.model, contents=history):
            if chunk.text:
                yield chunk.text


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, chat_history: list=[]) -> str:
        chat_history.append(self.construct_prompt(prompt, "user"))
        response = self.client.chat.completions.create(
            model=self.model,
            messages=chat_history
        )
        return response.choices[0].message.content
    
    async def generate_stream(self, prompt: str, chat_history: list=[]) -> Generator[str, None, None]:
        messages = chat_history + [{"role": "user", "content": prompt}]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class DeepSeekProvider(OpenAIProvider):
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(
            api_key=api_key, 
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = model