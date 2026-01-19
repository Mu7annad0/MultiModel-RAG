import re
import os
import string
import random
import aiofiles
import logging
import asyncio
from typing import List
from fastapi import UploadFile
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

import backend.prompts as prompt
from backend.cfg import load_settings


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

    async def validate(self, file: UploadFile):
        # check file type
        if file.content_type not in self.settings.FILE_FORMATS:
            return False, "Unsupported file format", None

        extension = os.path.splitext(file.filename)[1].lower()
        if extension != ".pdf":
            return False, "Unsupported file extension", None

        file_name = self._change_file_name(file.filename)
        file_path = os.path.join(self.files_dir, file_name)

        # save file
        try:
            async with aiofiles.open(file_path, "wb") as f:
                while chunk := await file.read(self.settings.FILE_CHUNK_SIZE):
                    await f.write(chunk)
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return False, str(e), None

        # check no of pages
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

    async def search(
        self,
        document_id: str,
        query: str,
        limit: int = 5,
        filter: bool = False,
        split: bool = False,
    ):
        collection_name = f"document_{document_id}"
        try:
            if split:
                self.logger.info("Splitting query...")
                sub_questions = await self.advancedrag_client.split_query(
                    prompt=prompt.SPLITTER_PROMPT, query=query
                )
                if not sub_questions:
                    sub_questions = [query]

                all_results = []
                seen_texts = set()

                self.logger.info(
                    "The query is split into {} sub-questions....".format(
                        len(sub_questions)
                    )
                )

                for sub_query in sub_questions:
                    embedding_result = await self.embedding_client.embed(text=sub_query)
                    if not embedding_result or len(embedding_result) == 0:
                        self.logger.warning(
                            f"Failed to generate embedding for sub-query: {sub_query}"
                        )
                        continue

                    vectors = embedding_result[0]
                    sub_results = await self.vdb_client.search(
                        collection_name=collection_name,
                        query_vector=vectors,
                        limit=limit,
                    )

                    for result in sub_results:
                        if result.text not in seen_texts:
                            all_results.append(result)
                            seen_texts.add(result.text)

                all_results.sort(key=lambda x: x.score, reverse=True)
                results = all_results[:limit]
                self.logger.info("Search results: length = {}".format(len(results)))
            else:
                embedding_result = await self.embedding_client.embed(text=query)
                if not embedding_result or len(embedding_result) == 0:
                    self.logger.error("Failed to generate embedding for query")
                    return []
                vectors = embedding_result[0]

                results = await self.vdb_client.search(
                    collection_name=collection_name, query_vector=vectors, limit=limit
                )
            if filter:
                indices = await self.advancedrag_client.filter_chunks(
                    prompt=prompt.FILTER_PROMPT, question=query, chunks=results
                )
                results = [results[i] for i in indices]
                self.logger.info("Filtered results: length = {}".format(len(results)))
            return results
        except Exception as e:
            self.logger.error(f"Error searching for document: {str(e)}")
            return []

    async def answer(
        self,
        document_id: str,
        query: str,
        chat_history: List = None,
        limit: int = 5,
        filter: bool = False,
        split: bool = False,
    ):
        retrieved_results = await self.search(document_id, query, limit, filter, split)
        if not retrieved_results:
            return None, []

        if not chat_history:
            system_content = prompt.SYSTEM_PROMPT.substitute()
            chat_history = [
                self.generation_client.construct_prompt(
                    query=system_content, role="system"
                )
            ]

        documents_prompt = "\n".join(
            prompt.DOCUMENT_PROMPT.substitute(doc_no=idx + 1, doc_content=doc.text)
            for idx, doc in enumerate(retrieved_results)
        )

        footer_text = prompt.FOOTER_PROMPT.substitute(query=query)

        final_prompt = f"{documents_prompt}\n\n{footer_text}"

        answer = await self.generation_client.answer(
            prompt=final_prompt, chat_history=chat_history
        )
        chat_history.append(
            self.generation_client.construct_prompt(query=query, role="user")
        )
        chat_history.append(
            self.generation_client.construct_prompt(query=answer, role="assistant")
        )

        if self.chat_history_manager:
            await self.chat_history_manager.save_history(document_id, chat_history)

        chunks = [
            f'In Page. {doc.metadata["page"]}:  "{doc.text}"'
            for doc in retrieved_results
        ]

        return answer, chunks

    async def answer_stream(
        self,
        document_id: str,
        query: str,
        chat_history: List = None,
        limit: int = 5,
        filter: bool = False,
        split: bool = False,
    ):
        retrieved_results = await self.search(document_id, query, limit, filter, split)
        if not retrieved_results:
            yield ("text", "No relevant documents found.")
            yield ("chunks", [])
            return

        self.logger.info(
            "Retrieved {} documents for document_id: {}".format(
                len(retrieved_results), document_id
            )
        )
        if not chat_history:
            system_content = prompt.SYSTEM_PROMPT.substitute()
            chat_history = [
                self.generation_client.construct_prompt(
                    query=system_content, role="system"
                )
            ]

        documents_prompt = "\n".join(
            prompt.DOCUMENT_PROMPT.substitute(doc_no=idx + 1, doc_content=doc.text)
            for idx, doc in enumerate(retrieved_results)
        )
        footer_text = prompt.FOOTER_PROMPT.substitute(query=query)
        final_prompt = f"{documents_prompt}\n\n{footer_text}"

        full_answer = ""
        async for chunk in await self.generation_client.answer_stream(
            prompt=final_prompt, chat_history=chat_history
        ):
            full_answer += chunk
            yield ("text", chunk)

        chat_history.append(
            self.generation_client.construct_prompt(query=query, role="user")
        )
        chat_history.append(
            self.generation_client.construct_prompt(query=full_answer, role="assistant")
        )

        if self.chat_history_manager:
            await self.chat_history_manager.save_history(document_id, chat_history)

        chunks = [
            f'In Page.{doc.metadata["page"]}:  "{doc.text}"'
            for doc in retrieved_results
        ]
        yield ("chunks", chunks)

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
