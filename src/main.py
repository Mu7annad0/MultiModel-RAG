import os
import uuid
import json
import logging
from fastapi import FastAPI, File, UploadFile, status, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from src.cfg import ChatRequest,Settings, load_settings
from src.controller import Controller
from src.logging import setup_logging
from src.clients import (
    EmbeddingClient,
    QrantVectorDB,
    GenerationClient,
    TTSClient,
    AdvancedRAGClient,
)
from src.chat_history import ChatHistoryManager


setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    try:
        settings = load_settings()
        app.vdb_client = QrantVectorDB(db_dir=settings.DB_DIR)
        await app.vdb_client.connect()
        app.embedding_client = EmbeddingClient(settings)
        app.tts_client = TTSClient(settings)
        app.chat_history_manager = ChatHistoryManager()
        app.audio_response_counter = 1
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise


@app.get("/")
async def print_info(app_settings: Settings = Depends(load_settings)):
    supported_file_types = app_settings.FILE_FORMATS
    max_file_pages = app_settings.FILE_PAGES

    return {
        "supported_file_types": supported_file_types,
        "max_file_pages": max_file_pages,
    }


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    settings: Settings = Depends(load_settings),
):
    try:
        logger.info(f"Received file upload request: {file.filename}")

        controller = Controller(
            embedding_client=app.embedding_client, vdb_client=app.vdb_client
        )

        logger.info("Validating file...")
        valid, message, file_path = await controller.validate(file=file)
        if not valid:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST, content={"error": message}
            )

        logger.info("Splitting text into chunks...")

        chunks, no_of_chunks = await controller.split_text(
            file_path=file_path,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

        logger.info(f"Created {no_of_chunks} chunks")

        document_id = str(uuid.uuid4())
        logger.info(f"Indexing document with ID: {document_id}")

        success, message = await controller.index_document(chunks, document_id)

        if not success:
            logger.error(f"Failed to index document: {message}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": message},
            )

        logger.info(f"Document indexed successfully: {document_id}")
        app.document_id = document_id
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Document indexed successfully",
                "document_id": document_id,
            },
        )

    except Exception as e:
        logger.error(f"Unhandled exception in upload_file: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Internal server error: {str(e)}"},
        )


@app.post("/chat")
async def chat(chat_request: ChatRequest):
    settings = load_settings()

    async def stream_generator():
        try:
            generation_client = GenerationClient(
                settings=settings,
                provider=chat_request.provider,
            )
            advancedrag_client = AdvancedRAGClient(settings)
        except Exception as e:
            logger.error(f"Failed to create generation client: {str(e)}", exc_info=True)
            yield json.dumps({"error": f"Internal server error: {str(e)}"})
            return

        history = await app.chat_history_manager.get_history(chat_request.document_id)

        controller = Controller(
            embedding_client=app.embedding_client,
            vdb_client=app.vdb_client,
            generation_client=generation_client,
            advancedrag_client=advancedrag_client,
            tts_client=app.tts_client,
            chat_history_manager=app.chat_history_manager,
            document_id=chat_request.document_id,
        )

        full_answer = ""
        try:
            async for event_type, data in controller.answer_stream(
                document_id=chat_request.document_id,
                query=chat_request.query,
                chat_history=history,
                filter=settings.FILTER,
                split=settings.SPLIT,
                limit=6,
            ):
                if event_type == "text":
                    full_answer += data
                    yield json.dumps({"type": "text", "content": data})
                elif event_type == "chunks":
                    yield json.dumps({"type": "chunks", "content": data})
        except Exception as e:
            logger.error(f"Error in streaming: {str(e)}", exc_info=True)
            yield json.dumps({"error": f"Streaming error: {str(e)}"})
            return

        if chat_request.generate_audio and full_answer:
            try:
                response_index = app.audio_response_counter
                app.audio_response_counter += 1
                audio_file = await controller.generate_audio(
                    full_answer, response_index
                )
                if audio_file:
                    yield json.dumps({"type": "audio", "content": str(audio_file)})
            except Exception as e:
                logger.error(f"Error generating audio: {str(e)}", exc_info=True)

    if settings.STREAMING:

        async def event_generator():
            async for item in stream_generator():
                yield f"data: {item}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        generation_client = GenerationClient(
            settings=settings,
            provider=chat_request.provider,
        )
        advancedrag_client = AdvancedRAGClient(settings)
        logger.info(f"Generation client created with provider: {chat_request.provider}")
    except Exception as e:
        logger.error(f"Failed to create generation client: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Internal server error: {str(e)}"},
        )

    history = await app.chat_history_manager.get_history(chat_request.document_id)

    controller = Controller(
        embedding_client=app.embedding_client,
        vdb_client=app.vdb_client,
        generation_client=generation_client,
        advancedrag_client=advancedrag_client,
        tts_client=app.tts_client,
        chat_history_manager=app.chat_history_manager,
        document_id=chat_request.document_id,
    )
    audio_file = None

    answer, chunks = await controller.answer(
        document_id=chat_request.document_id,
        query=chat_request.query,
        chat_history=history,
        filter=settings.FILTER,
        split=settings.SPLIT,
        limit=6,
    )
    if not answer:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to generate answer"},
        )

    if chat_request.generate_audio:
        logger.info("Generating audio...")
        response_index = app.audio_response_counter
        app.audio_response_counter += 1
        audio_file = await controller.generate_audio(answer, response_index)
        if not audio_file:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Failed to generate audio"},
            )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "answer": answer,
            "chunks": chunks,
            "audio_file": str(audio_file) if audio_file else None,
        },
    )


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve audio files from the voices directory."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    voices_dir = os.path.join(base_dir, "voices")
    file_path = os.path.join(voices_dir, filename)

    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    else:
        logger.error(f"Audio file not found: {file_path}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Audio file not found"},
        )
