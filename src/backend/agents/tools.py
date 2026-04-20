import json
import logging
from typing import List, Dict, Any
from langchain_core.tools import tool

from backend.clients.vdb import RetrievedDocument, QrantVectorDB
from backend.clients.embedding import EmbeddingClient
from backend.agents.prompts import FILTER_PROMPT, SPLITTER_PROMPT
from langchain_openai import ChatOpenAI


logger = logging.getLogger(__name__)


class SearchTool:
    def __init__(
        self,
        embedding_client: EmbeddingClient,
        vdb_client: QrantVectorDB,
        settings: Any,
    ):
        self.embedding_client = embedding_client
        self.vdb_client = vdb_client
        self.settings = settings
        self.filter_client = None
        if settings.FILTER:
            api_key = getattr(settings, "OPENAI_API_KEY", None)
            if api_key:
                self.filter_client = ChatOpenAI(api_key=api_key, model="gpt-5-mini")

    async def search(
        self,
        query: str,
        document_id: str,
        use_split: bool = False,
        use_filter: bool = False,
        limit: int = 6,
    ) -> Dict[str, Any]:

        collection_name = f"document_{document_id}"
        queries_to_search = [query]

        if use_split:
            logger.info("Splitting query into sub-queries...")
            sub_queries = await self._split_query(query)
            if sub_queries and len(sub_queries) > 0:
                queries_to_search = sub_queries
                logger.info(f"Query split into {len(sub_queries)} sub-queries")

        all_results = []
        seen_texts = set()

        for search_query in queries_to_search:
            logger.info(f"Searching with query: {search_query}")

            embedding_result = await self.embedding_client.embed(text=search_query)
            if not embedding_result or len(embedding_result) == 0:
                logger.warning(
                    f"Failed to generate embedding for query: {search_query}"
                )
                continue

            vectors = embedding_result[0]

            try:
                results = await self.vdb_client.search(
                    collection_name=collection_name,
                    query_vector=vectors,
                    limit=limit,
                )

                for result in results:
                    if result.text not in seen_texts:
                        all_results.append(result)
                        seen_texts.add(result.text)

            except Exception as e:
                logger.error(f"Error searching for query '{search_query}': {str(e)}")

        all_results.sort(key=lambda x: x.score, reverse=True)
        all_results = all_results[:limit]

        logger.info(f"Total unique results found: {len(all_results)}")

        if use_filter and self.filter_client and all_results:
            logger.info("Filtering chunks for relevance...")
            indices = await self._filter_chunks(query, all_results)
            all_results = [all_results[i] for i in indices if i < len(all_results)]
            logger.info(f"Filtered to {len(all_results)} relevant chunks")

        return {
            "chunks": all_results,
            "total_found": len(all_results),
            "queries_used": queries_to_search,
        }

    async def _split_query(self, query: str) -> List[str]:
        try:
            split_prompt = SPLITTER_PROMPT.substitute(question=query)
            response = await self.filter_client.ainvoke(
                [{"role": "user", "content": split_prompt}]
            )

            content = response.content
            if not isinstance(content, str):
                content = str(content) if content else ""

            parsed = json.loads(content)
            return parsed.get("decomposed_questions", [query])

        except (json.JSONDecodeError, TypeError, Exception) as e:
            logger.warning(f"Error splitting query: {str(e)}")
            return [query]

    async def _filter_chunks(
        self, question: str, chunks: List[RetrievedDocument]
    ) -> List[int]:
        try:
            formatted_chunks = "\n".join(
                f"Chunk {i}: {chunk.text}" for i, chunk in enumerate(chunks)
            )

            filter_prompt = FILTER_PROMPT.substitute(
                question=question,
                chunks=formatted_chunks,
            )

            response = await self.filter_client.ainvoke(
                [{"role": "user", "content": filter_prompt}]
            )

            content = response.content
            if not isinstance(content, str):
                content = str(content) if content else ""

            parsed = json.loads(content)
            return parsed.get("relevant_chunk_indices", list(range(len(chunks))))

        except (json.JSONDecodeError, TypeError, Exception) as e:
            logger.warning(f"Error filtering chunks: {str(e)}")
            return list(range(len(chunks)))


def create_search_tool(embedding_client, vdb_client, settings):
    search_tool = SearchTool(embedding_client, vdb_client, settings)

    @tool
    async def search_document(
        query: str,
        document_id: str,
        use_split: bool = False,
        use_filter: bool = False,
        limit: int = 6,
    ) -> str:
        result = await search_tool.search(
            query=query,
            document_id=document_id,
            use_split=use_split,
            use_filter=use_filter,
            limit=limit,
        )

        result["chunks"] = [
            {"text": chunk.text, "score": chunk.score, "metadata": chunk.metadata}
            for chunk in result["chunks"]
        ]

        return json.dumps(result)

    return search_document
