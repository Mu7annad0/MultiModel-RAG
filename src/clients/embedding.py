import logging
from typing import Union, List
from openai import OpenAI
from cohere import Client as Cohere
from google import genai
from google.genai import types


class EmbeddingClient:
    def __init__(self, settings):
        self.settings = settings
        self.client = None
        self.logger = logging.getLogger(__name__)
    
    def embed(self, text: Union[str, List[str]]):
        input_type = "search_document"
        if isinstance(text, str):
            text = [text]
            input_type = "search_query"
        
        if self.settings.EMBEDDING_PROVIDER == "openai":
            self.client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
            self.logger.info(f"Embedding texts using OpenAI")
            try:
                response = self.client.embeddings.create(
                    input=text,
                    model=self.settings.OPENAI_EMBEDDING_MODEL,
                    dimensions=self.settings.EMBEDDING_DIMENSION
                )
                if not response or not response.data or len(response.data) == 0 or not response.data[0].embedding:
                    self.logger.error("Error while embedding text with OpenAI")
                    return None
                return [res.embedding for res in response.data]
            except Exception as e:
                self.logger.error(f"Error while embedding text with OpenAI: {str(e)}")
                return None

        if self.settings.EMBEDDING_PROVIDER == "gemini":
            self.client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
            self.logger.info(f"Embedding texts using Google")
            try:
                response = self.client.models.embed_content(
                    model=self.settings.GEMINI_EMBEDDING_MODEL,
                    contents=text,
                    config=types.EmbedContentConfig(
                        output_dimensionality=self.settings.EMBEDDING_DIMENSION
                    )
                )
                if not response.embeddings:
                    self.logger.error("No embeddings returned by Google")
                    return None
                return [res.values for res in response.embeddings]
            except Exception as e:
                self.logger.error(f"Error while embedding text with Google: {str(e)}")
                return None
        
        if self.settings.EMBEDDING_PROVIDER == "cohere":
            self.client = Cohere(api_key=self.settings.COHERE_API_KEY)
            self.logger.info(f"Embedding texts using Cohere")
            try:
                response = self.client.embed(
                    model=self.settings.COHERE_EMBEDDING_MODEL,
                    texts=text,
                    embedding_types=['float'],
                    input_type=input_type
                )
                if not response.embeddings:
                    self.logger.error("No embeddings returned by Cohere")
                    return None
                return [e for e in response.embeddings.float]
            except Exception as e:
                self.logger.error(f"Error while embedding text with Cohere: {str(e)}")
                return None
        