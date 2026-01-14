import re
import os
import string
import random
import aiofiles
from fastapi import UploadFile
from langchain_community.document_loaders import PyMuPDFLoader

from src.cfg import load_settings


class DataController:
    def __init__(self):
        self.settings = load_settings()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.files_dir = os.path.join(self.base_dir, "assets/files")
        os.makedirs(self.files_dir, exist_ok=True)
    
    async def validate(self, file: UploadFile):
        # check file type
        if file.content_type not in self.settings.FILE_FORMATS:
            return False, "Unsupported file format"
        
        extension = os.path.splitext(file.filename)[1].lower()
        if extension != ".pdf":
            return False, "Unsupported file extension"
        
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
            return False, str(e)
        
        # check no of pages
        try:
            loader = PyMuPDFLoader(file_path)
            no_pages = sum(1 for _ in loader.lazy_load())
            
            if no_pages > self.settings.FILE_PAGES:
                os.remove(file_path)
                return False, f"File has {no_pages} pages, max allowed is {self.settings.FILE_PAGES}"
            
            return True, "File uploaded successfully"
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return False, f"Error processing PDF: {str(e)}"

    def _change_file_name(self, current_name: str) -> str:
        cleaned_name = re.sub(r'[^\w.\-]', '', current_name.strip()).replace(" ", "_")
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        return f"{random_string}_{cleaned_name}"
        
