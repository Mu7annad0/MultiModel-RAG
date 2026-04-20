import logging
from typing import Union, List
import asyncio
from openai import AsyncOpenAI
from cohere import AsyncClient as AsyncCohere
from google import genai
from google.genai import types


class EmbeddingClient:
    def __init__(self, settings):
        self.settings = settings
        self.client = None
        self.logger = logging.getLogger(__name__)

    async def embed(self, text: Union[str, List[str]]):
        input_type = "search_document"
        if isinstance(text, str):
            text = [text]
            input_type = "search_query"

        if self.settings.EMBEDDING_PROVIDER == "openai":
            self.client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
            self.logger.info(f"Embedding texts using OpenAI")
            try:
                response = await self.client.embeddings.create(
                    input=text,
                    model=self.settings.OPENAI_EMBEDDING_MODEL,
                    dimensions=self.settings.EMBEDDING_DIMENSION,
                )
                if (
                    not response
                    or not response.data
                    or len(response.data) == 0
                    or not response.data[0].embedding
                ):
                    self.logger.error("Error while embedding text with OpenAI")
                    return None
                self.logger.info(f"Successfully embedded text with OpenAI")
                return [res.embedding for res in response.data]
            except Exception as e:
                self.logger.error(f"Error while embedding text with OpenAI: {str(e)}")
                return None

        if self.settings.EMBEDDING_PROVIDER == "gemini":
            self.client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
            self.logger.info(f"Embedding texts using Google")
            try:
                batch_size = 100
                all_embeddings = []
                for i in range(0, len(text), batch_size):
                    batch = text[i : i + batch_size]
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda b=batch: self.client.models.embed_content(
                            model=self.settings.GEMINI_EMBEDDING_MODEL,
                            contents=b,
                            config=types.EmbedContentConfig(
                                output_dimensionality=self.settings.EMBEDDING_DIMENSION
                            ),
                        ),
                    )
                    if not response.embeddings:
                        self.logger.error("No embeddings returned by Google")
                        return None
                    all_embeddings.extend([res.values for res in response.embeddings])
                self.logger.info(f"Successfully embedded text with Google")
                return all_embeddings
            except Exception as e:
                self.logger.error(f"Error while embedding text with Google: {str(e)}")
                return None

        if self.settings.EMBEDDING_PROVIDER == "cohere":
            self.client = AsyncCohere(api_key=self.settings.COHERE_API_KEY)
            self.logger.info(f"Embedding texts using Cohere")
            try:
                response = await self.client.embed(
                    model=self.settings.COHERE_EMBEDDING_MODEL,
                    texts=text,
                    embedding_types=["float"],
                    input_type=input_type,
                )
                if not response.embeddings:
                    self.logger.error("No embeddings returned by Cohere")
                    return None
                self.logger.info(f"Successfully embedded text with Cohere")
                return [e for e in response.embeddings.float]
            except Exception as e:
                self.logger.error(f"Error while embedding text with Cohere: {str(e)}")
                return None
        return None
