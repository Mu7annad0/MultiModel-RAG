import re
import os
import string
import random
import aiofiles
import logging
import asyncio
import json
from typing import List, Dict, Any, AsyncGenerator
from fastapi import UploadFile
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import backend.prompts as prompt
from backend.cfg import load_settings
from backend.agents import create_rag_agent


class Controller:
    def __init__(
        self,
        embedding_client,
        vdb_client,
        generation_client=None,
        advancedrag_client=None,
        tts_client=None,
        chat_history_manager=None,
        document_id=None,
        eval_client=None,
    ):
        self.settings = load_settings()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.files_dir = os.path.join(self.base_dir, "assets", "files")
        os.makedirs(self.files_dir, exist_ok=True)
        self.embedding_client = embedding_client
        self.vdb_client = vdb_client
        self.generation_client = generation_client
        self.advancedrag_client = advancedrag_client
        self.eval_client = eval_client
        self.tts_client = tts_client
        self.chat_history_manager = chat_history_manager
        self.document_id = document_id
        self.logger = logging.getLogger(__name__)
        self._agent = None
        self._current_provider = None

    def _get_agent(self):
        provider = None
        if self.generation_client and hasattr(self.generation_client, "provider"):
            provider = getattr(self.generation_client.provider, "model", None)

        if self._agent is None or self._current_provider != provider:
            if self._agent is not None:
                self.logger.info(
                    f"Provider changed from {self._current_provider} to {provider}, recreating agent"
                )
            self.logger.info("Initializing LangGraph RAG agent...")
            self._agent = create_rag_agent(
                settings=self.settings,
                embedding_client=self.embedding_client,
                vdb_client=self.vdb_client,
                generation_client=self.generation_client,
            )
            self._current_provider = provider
        return self._agent

    async def validate(self, file: UploadFile):
        if file.content_type not in self.settings.FILE_FORMATS:
            return False, "Unsupported file format", None

        extension = os.path.splitext(file.filename)[1].lower()
        if extension != ".pdf":
            return False, "Unsupported file extension", None

        file_name = self._change_file_name(file.filename)
        file_path = os.path.join(self.files_dir, file_name)

        try:
            async with aiofiles.open(file_path, "wb") as f:
                while chunk := await file.read(self.settings.FILE_CHUNK_SIZE):
                    await f.write(chunk)
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return False, str(e), None

        try:
            loop = asyncio.get_event_loop()
            no_pages = await loop.run_in_executor(
                None, lambda: self._count_pdf_pages(file_path)
            )

            if no_pages > self.settings.FILE_PAGES:
                os.remove(file_path)
                return (
                    False,
                    f"File has {no_pages} pages, max allowed is {self.settings.FILE_PAGES}",
                    None,
                )
            return True, "File uploaded successfully", file_path

        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return False, f"Error processing PDF: {str(e)}", None

    def _count_pdf_pages(self, file_path: str) -> int:
        loader = PyMuPDFLoader(file_path)
        return sum(1 for _ in loader.lazy_load())

    async def split_text(self, file_path: str, chunk_size: int, chunk_overlap: int):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._split_text_blocking(file_path, chunk_size, chunk_overlap),
        )

    def _split_text_blocking(self, file_path: str, chunk_size: int, chunk_overlap: int):
        loader = PyMuPDFLoader(file_path)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

        documents = loader.load()

        file_content_text = [rec.page_content for rec in documents]
        file_content_metadata = [rec.metadata for rec in documents]

        chunks = text_splitter.create_documents(
            file_content_text, file_content_metadata
        )
        return chunks, len(chunks)

    async def index_document(self, chunks: List[str], document_id: str):
        try:
            index_name = f"document_{document_id}"
            success = await self.vdb_client.create_collection(
                collection_name=index_name,
                vector_size=self.settings.EMBEDDING_DIMENSION,
                provider=self.settings.EMBEDDING_PROVIDER,
            )
            if not success:
                return False, "Failed to create collection"

            texts = [chunk.page_content for chunk in chunks]
            metadata = [chunk.metadata for chunk in chunks]

            embeddings = await self.embedding_client.embed(text=texts)
            success = await self.vdb_client.insert(
                collection_name=index_name,
                texts=texts,
                vectors=embeddings,
                metadata=metadata,
            )

            if not success:
                return False, "Failed to insert documents"

            return True, "Documents inserted successfully"
        except Exception as e:
            return False, f"Error indexing document: {str(e)}"

    async def answer(
        self,
        document_id: str,
        query: str,
        chat_history: List = None,
        limit: int = 6,
        use_filter: bool = False,
        use_split: bool = False,
    ):
        self.logger.info(f"Processing query with agent: {query}")

        agent = self._get_agent()

        try:
            result = await agent.ainvoke(
                {
                    "document_id": document_id,
                    "original_query": query,
                    "chat_history": chat_history or [],
                    "use_split": use_split,
                    "use_filter": use_filter,
                    "limit": limit,
                    "search_iterations": 0,
                    "max_iterations": 3,
                    "needs_search": True,
                    "search_reasoning": "",
                    "current_query": query,
                    "sub_queries": None,
                    "retrieved_chunks": [],
                    "total_chunks_found": 0,
                    "queries_used": [],
                    "evaluation_result": "",
                    "refinement_reason": None,
                    "final_answer": "",
                    "error": None,
                }
            )

            answer = result.get("final_answer", "")
            chunks = result.get("retrieved_chunks", [])
            updated_history = result.get("chat_history", [])

            formatted_chunks = [
                f'In Page. {doc.metadata.get("page", "unknown")}:  "{doc.text}"'
                for doc in chunks
            ]

            if self.chat_history_manager:
                await self.chat_history_manager.save_history(
                    document_id, updated_history
                )

            self.logger.info(f"Agent completed. Retrieved {len(chunks)} chunks.")

            return answer, formatted_chunks

        except Exception as e:
            self.logger.error(f"Error in agent answer: {str(e)}", exc_info=True)
            return f"Error processing your request: {str(e)}", []

    async def answer_stream(
        self,
        document_id: str,
        query: str,
        chat_history: List = None,
        limit: int = 6,
        use_filter: bool = False,
        use_split: bool = False,
    ):
        self.logger.info(f"Processing streaming query with agent: {query}")

        agent = self._get_agent()

        try:
            initial_state = {
                "document_id": document_id,
                "original_query": query,
                "chat_history": chat_history or [],
                "use_split": use_split,
                "use_filter": use_filter,
                "limit": limit,
                "search_iterations": 0,
                "max_iterations": 3,
                "needs_search": True,
                "search_reasoning": "",
                "current_query": query,
                "sub_queries": None,
                "retrieved_chunks": [],
                "total_chunks_found": 0,
                "queries_used": [],
                "evaluation_result": "",
                "refinement_reason": None,
                "generation_prompt": None,
                "final_answer": "",
                "error": None,
            }

            full_answer = ""
            retrieved_chunks = []
            updated_history = []
            generation_prompt = ""

            async for event in agent.astream_events(initial_state, version="v1"):
                event_type = event.get("event", "")
                node_name = event.get("name", "")

                if event_type == "on_chain_start" and node_name == "analyze_query":
                    yield (
                        "reasoning",
                        "Analyzing query to determine if document search is needed...",
                    )

                elif event_type == "on_chain_end" and node_name == "analyze_query":
                    output = event.get("data", {}).get("output", {})
                    needs_search = output.get("needs_search", True)
                    reasoning = output.get("search_reasoning", "")
                    decision = (
                        "Search needed" if needs_search else "Using chat history only"
                    )
                    yield ("reasoning", f"Decision: {decision}. {reasoning}")

                elif event_type == "on_chain_start" and node_name == "search":
                    input_data = event.get("data", {}).get("input", {})
                    current_query = input_data.get("current_query", query)
                    yield (
                        "reasoning",
                        f"Searching document with query: {current_query}",
                    )

                elif event_type == "on_chain_end" and node_name == "search":
                    output = event.get("data", {}).get("output", {})
                    try:
                        if isinstance(output, str):
                            search_result = json.loads(output)
                        elif isinstance(output, dict):
                            search_result = output
                        else:
                            search_result = {}

                        total_found = search_result.get("total_found", 0)
                        yield ("reasoning", f"Found {total_found} relevant chunks")
                    except:
                        yield ("reasoning", "Search completed")

                elif event_type == "on_chain_start" and node_name == "evaluate_results":
                    yield ("reasoning", "Evaluating if results are sufficient...")

                elif event_type == "on_chain_end" and node_name == "evaluate_results":
                    output = event.get("data", {}).get("output", {})
                    result = output.get("evaluation_result", "sufficient")
                    reason = output.get("refinement_reason", "")

                    if result == "refine":
                        yield ("reasoning", f"Results insufficient. Refining: {reason}")
                    elif result == "sufficient":
                        yield ("reasoning", "Results are sufficient for answering")
                    else:
                        yield ("reasoning", f"Evaluation: {result}")

                elif event_type == "on_chain_start" and node_name == "refine_query":
                    input_data = event.get("data", {}).get("input", {})
                    reason = input_data.get("refinement_reason", "")
                    yield ("reasoning", f"Refining search strategy: {reason}")

                elif (
                    event_type == "on_chain_start" and node_name == "generate_response"
                ):
                    yield ("reasoning", "Generating final answer...")

                elif event_type == "on_chain_end" and node_name == "generate_response":
                    output = event.get("data", {}).get("output", {})
                    generation_prompt = output.get("generation_prompt", "")
                    updated_history = output.get("chat_history", [])

                elif event_type == "on_chain_end" and node_name == "search":
                    output = event.get("data", {}).get("output", {})
                    try:
                        chunks_from_search = output.get("retrieved_chunks", [])
                        if chunks_from_search:
                            retrieved_chunks = chunks_from_search
                    except:
                        pass

            yield ("reasoning", "Preparing response (this may take 10-15 seconds)...")
            full_answer = ""

            if generation_prompt and self.generation_client:
                try:
                    messages = []
                    if chat_history:
                        messages.extend(chat_history)

                    self.logger.info("Connecting to LLM API...")
                    token_count = 0
                    start_time = asyncio.get_event_loop().time()

                    async for content in self.generation_client.answer_stream(
                        generation_prompt, messages
                    ):
                        if token_count == 0:
                            elapsed = asyncio.get_event_loop().time() - start_time
                            self.logger.info(
                                f"First token received after {elapsed:.2f}s"
                            )
                            yield (
                                "reasoning",
                                f"Generating response (connected in {elapsed:.1f}s)...",
                            )
                        token_count += 1
                        if content:
                            full_answer += content
                            yield ("text", content)

                    self.logger.info(
                        f"Streaming generation complete. Length: {len(full_answer)}"
                    )
                except Exception as e:
                    self.logger.error(f"Error in streaming generation: {str(e)}")
                    error_msg = f"Error generating response: {str(e)}"
                    yield ("text", error_msg)
                    full_answer = error_msg
            else:
                self.logger.error("No generation prompt or LLM available")
                yield ("text", "Error: Could not prepare generation")
                full_answer = "Error: Could not prepare generation"

            if retrieved_chunks:
                formatted_chunks = [
                    f'In Page.{doc.metadata.get("page", "unknown")}:  "{doc.text}"'
                    for doc in retrieved_chunks
                ]
                yield ("chunks", formatted_chunks)

            if self.chat_history_manager:
                await self.chat_history_manager.save_history(
                    document_id, updated_history
                )

            self.logger.info(
                f"Streaming agent completed. Answer length: {len(full_answer)}"
            )

        except Exception as e:
            self.logger.error(f"Error in streaming agent: {str(e)}", exc_info=True)
            yield ("text", f"Error processing your request: {str(e)}")
            yield ("chunks", [])

    async def evaluate_answer(self, query: str, answer: str, retrieved_results):
        if self.eval_client:
            answer_relevancy, faithfulness = await self.eval_client.evaluate(
                query, answer, retrieved_results
            )
            return answer_relevancy, faithfulness
        return None, None

    async def generate_audio(self, query: str, response_index: int):
        if self.tts_client:
            return await self.tts_client.generate(query, response_index)
        return None

    def _change_file_name(self, current_name: str) -> str:
        cleaned_name = re.sub(r"[^\w.\-]", "", current_name.strip()).replace(" ", "_")
        random_string = "".join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )
        return f"{random_string}_{cleaned_name}"
