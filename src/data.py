import re
import os
import string
import random
import aiofiles
from fastapi import UploadFile
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.cfg import load_settings


class DataController:
    def __init__(self, embedding_client):
        self.settings = load_settings()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.files_dir = os.path.join(self.base_dir, "assets/files")
        os.makedirs(self.files_dir, exist_ok=True)
        self.embedding_client = embedding_client
    
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
                return False, f"File has {no_pages} pages, max allowed is {self.settings.FILE_PAGES}", None
            
            return True, "File uploaded successfully", file_path
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return False, f"Error processing PDF: {str(e)}", None
        

    def split_text(self, file_path: str, chunk_size: int, chunk_overlap: int):
        loader = PyMuPDFLoader(file_path)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        documents = loader.load()

        file_content_text = [
            rec.page_content for rec in documents
        ]
        file_content_metadata = [
            rec.metadata for rec in documents
        ]

        chunks = text_splitter.create_documents(file_content_text, file_content_metadata)
        return chunks, len(chunks)


    def index(self,text):
        return self.embedding_client.embed(text)
        ## TODO: Implementing vector store


    def _change_file_name(self, current_name: str) -> str:
        cleaned_name = re.sub(r'[^\w.\-]', '', current_name.strip()).replace(" ", "_")
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        return f"{random_string}_{cleaned_name}"
