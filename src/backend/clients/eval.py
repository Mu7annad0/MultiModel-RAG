from typing import List
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings.base import embedding_factory
from ragas.metrics.collections import AnswerRelevancy, Faithfulness


class EvaluationClient:
    def __init__(self, settings):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.llm = llm_factory(settings.EVALUATION_MODEL, client=self.client)
        self.embedding = embedding_factory("openai", model=settings.OPENAI_EMBEDDING_MODEL, client=self.client)
        self.answer_relevancy = AnswerRelevancy(llm=self.llm, embeddings=self.embedding)
        self.faithfulness = Faithfulness(llm=self.llm)

    async def evaluate(self, user_query: str, answer: str, retrieved_chunks: List[str]):
        answer_relevancy_result = await self.answer_relevancy.ascore(
            user_input=user_query, 
            response=answer)

        faithfulness_result = await self.faithfulness.ascore(
            user_input=user_query, 
            response=answer, 
            retrieved_contexts=retrieved_chunks)
        return answer_relevancy_result.value, faithfulness_result.value
