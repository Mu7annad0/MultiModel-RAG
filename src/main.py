from fastapi import FastAPI, File, UploadFile, status, Depends
from fastapi.responses import JSONResponse

from src.cfg import Settings, load_settings
from src.data import DataController
from src.clients.embedding import EmbeddingClient


app = FastAPI()

@app.get("/")
async def print_info(app_settings: Settings = Depends(load_settings)):
    supported_file_types = app_settings.FILE_FORMATS
    max_file_pages = app_settings.FILE_PAGES

    return {
        "supported_file_types": supported_file_types,
        "max_file_pages": max_file_pages
    }


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    settings: Settings = Depends(load_settings),
):
    embedding_client = EmbeddingClient(settings)
    data_controller = DataController(embedding_client)
    
    valid, message, file_path = await data_controller.validate(file=file)
    if not valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, 
            content={
                "error": message
            }
        )
    
    chunks, no_of_chunks = data_controller.split_text(
        file_path=file_path,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )
    # Extract text content from Document objects
    chunk_texts = [chunk.page_content for chunk in chunks]

    embeddings = data_controller.index(chunk_texts)
    return JSONResponse(
        status_code=status.HTTP_200_OK, 
        content={
            "message": "processed correctly",
            "embeddings": embeddings[:1]
        }
    )
