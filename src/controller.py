import re
import os
import string
import random
import aiofiles
from typing import List, Literal, Generator
from pydantic import BaseModel
from fastapi import UploadFile
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

import src.prompts as prompt
from src.cfg import load_settings


class Controller:
    def __init__(
        self,
        embedding_client,
        vdb_client,
        generation_client=None,
        tts_client=None,
        chat_history_manager=None,
        document_id=None,
    ):
        self.settings = load_settings()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.files_dir = os.path.join(self.base_dir, "assets/files")
        os.makedirs(self.files_dir, exist_ok=True)
        self.embedding_client = embedding_client
        self.vdb_client = vdb_client
        self.generation_client = generation_client
        self.tts_client = tts_client
        self.chat_history_manager = chat_history_manager
        self.document_id = document_id

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
            loader = PyMuPDFLoader(file_path)
            no_pages = sum(1 for _ in loader.lazy_load())

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

    def split_text(self, file_path: str, chunk_size: int, chunk_overlap: int):
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

    def index_document(self, chunks: List[str], document_id: str):
        try:
            index_name = f"document_{document_id}"
            success = self.vdb_client.create_collection(
                collection_name=index_name,
                vector_size=self.settings.EMBEDDING_DIMENSION,
            )
            if not success:
                return False, "Failed to create collection"

            texts = [chunk.page_content for chunk in chunks]
            metadata = [chunk.metadata for chunk in chunks]

            embeddings = self.embedding_client.embed(text=texts)
            success = self.vdb_client.insert(
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

    def search(self, document_id: str, query: str, limit: int = 5):
        collection_name = f"document_{document_id}"
        try:
            vectors = self.embedding_client.embed(text=query)[0]
            results = self.vdb_client.search(
                collection_name=collection_name, query_vector=vectors, limit=5
            )
            return results
        except Exception as e:
            return False, f"Error searching document: {str(e)}"

    def answer(self, document_id: str, query: str, chat_history: List = None, limit: int = 5):
        retrieved_results = self.search(document_id, query, limit)
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

        answer = self.generation_client.answer(
            prompt=final_prompt, chat_history=chat_history
        )
        chat_history.append(
            self.generation_client.construct_prompt(query=query, role="user")
        )
        chat_history.append(
            self.generation_client.construct_prompt(query=answer, role="assistant")
        )

        if self.chat_history_manager:
            self.chat_history_manager.save_history(document_id, chat_history)

        chunks = [
            f'In Page. {doc.metadata["page"]}:  "{doc.text}"'
            for doc in retrieved_results
        ]

        return answer, chunks

    def answer_stream(
        self, document_id: str, query: str, chat_history: List = None, limit: int = 5
    ):
        retrieved_results = self.search(document_id, query, limit)
        if not retrieved_results:
            yield ("text", "No relevant documents found.")
            yield ("chunks", [])
            return

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
        for chunk in self.generation_client.answer_stream(
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
            self.chat_history_manager.save_history(document_id, chat_history)

        chunks = [
            f'In Page.{doc.metadata["page"]}:  "{doc.text}"'
            for doc in retrieved_results
        ]
        yield ("chunks", chunks)

    def generate_audio(self, query: str, response_index: int):
        if self.tts_client:
            return self.tts_client.generate(query, response_index)
        return None

    def _change_file_name(self, current_name: str) -> str:
        cleaned_name = re.sub(r"[^\w.\-]", "", current_name.strip()).replace(" ", "_")
        random_string = "".join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )
        return f"{random_string}_{cleaned_name}"


class ChatRequest(BaseModel):
    document_id: str
    query: str
    provider: Literal["openai", "gemini", "deepseek"]
    generate_audio: bool
