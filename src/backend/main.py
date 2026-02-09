import os
import uuid
import json
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, File, UploadFile, status, Depends
from sqlalchemy import update
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.cfg import ChatRequest, Settings, load_settings
from backend.controller import Controller
from backend.app_logging import setup_logging
from backend.clients import (
    EmbeddingClient,
    QrantVectorDB,
    GenerationClient,
    TTSClient,
    AdvancedRAGClient,
    EvaluationClient,
    AdvancedRAGClient,
)
from backend.db.chat_history_db import ChatHistoryManagerDB
from backend.db.database import DBChat, db_client
import backend.prompts as prompt


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
        app.settings = load_settings()
        app.vdb_client = QrantVectorDB(db_dir=app.settings.DB_DIR)
        await app.vdb_client.connect()
        app.embedding_client = EmbeddingClient(app.settings)
        app.advanced_rag_client = AdvancedRAGClient(app.settings)
        app.tts_client = TTSClient(app.settings)
        app.chat_history_manager = ChatHistoryManagerDB()
        app.audio_response_counter = 1

        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise


class NewChatRequest(BaseModel):
    first_message: str
    document_id: Optional[str] = None


class UpdateChatTitleRequest(BaseModel):
    message: str


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
    chat_id: Optional[int] = None,
    settings: Settings = Depends(load_settings),
):
    try:
        logger.info(
            f"Received file upload request: {file.filename}, chat_id: {chat_id}"
        )

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

        new_chat_id = None
        # If no chat_id is provided, create a new chat with generic name
        # The title will be updated after the first user message
        if not chat_id:
            chat_title = "new chat"
            new_chat_id = await app.chat_history_manager.create_chat(
                chat_name=chat_title, document_id=document_id
            )
            chat_id = new_chat_id
            logger.info(f"Created new chat {chat_id} for document {document_id}")
        else:
            async with db_client() as session:
                stmt = (
                    update(DBChat)
                    .where(DBChat.id == chat_id)
                    .values(document_id=document_id)
                )
                await session.execute(stmt)
                await session.commit()
            logger.info(f"Associated document {document_id} with chat {chat_id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Document indexed successfully",
                "document_id": document_id,
                "filename": file.filename,
                "chat_id": chat_id,
            },
        )

    except Exception as e:
        logger.error(f"Unhandled exception in upload_file: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Internal server error: {str(e)}"},
        )


@app.post("/new_chat")
async def new_chat(request: NewChatRequest):
    try:
        # Use 'new chat' as default title - will be updated after first user query
        chat_title = "new chat"

        chat_id = await app.chat_history_manager.create_chat(
            chat_name=chat_title, document_id=request.document_id
        )

        logger.info(f"Created new chat with ID: {chat_id}, title: {chat_title}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "chat_id": chat_id,
                "chat_name": chat_title,
                "message": "Chat created successfully",
            },
        )
    except Exception as e:
        logger.error(f"Error creating new chat: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to create chat: {str(e)}"},
        )


@app.get("/chats")
async def list_chats():
    """Get all chats ordered by most recently updated."""
    try:
        chats = await app.chat_history_manager.get_all_chats()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"chats": chats},
        )
    except Exception as e:
        logger.error(f"Error listing chats: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to list chats: {str(e)}"},
        )


@app.get("/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: int):
    """Get all messages for a specific chat."""
    try:
        # Check if chat exists
        chat = await app.chat_history_manager.get_chat(chat_id)
        if not chat:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Chat not found"},
            )

        messages = await app.chat_history_manager.get_messages(chat_id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "chat": chat,
                "messages": messages,
            },
        )
    except Exception as e:
        logger.error(f"Error getting chat messages: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get messages: {str(e)}"},
        )


@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: int):
    """Delete a chat and all its messages."""
    try:
        success = await app.chat_history_manager.delete_chat(chat_id)

        if not success:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Chat not found"},
            )

        logger.info(f"Deleted chat with ID: {chat_id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Chat deleted successfully"},
        )
    except Exception as e:
        logger.error(f"Error deleting chat: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to delete chat: {str(e)}"},
        )


@app.patch("/chats/{chat_id}")
async def update_chat_title(chat_id: int, request: UpdateChatTitleRequest):
    """Generate and update a chat's title from a message."""
    try:
        # Generate title from the message
        title = "Untitled Chat"
        
        try:
            title = await app.advanced_rag_client.generate_chat_title(
                prompt.CHAT_TITLE_PROMPT, request.message
            )
            
            # Clean and validate the generated title
            title = title.strip().strip("\"'").strip()
            
            if len(title) > 100:
                title = title[:97] + "..."
            
            # Ensure we have a valid title
            if not title:
                title = "Untitled Chat"
                
        except Exception as e:
            logger.error(f"Error generating chat title: {str(e)}")
            # title already set to default above

        logger.info(f"Generated title: {title} for chat {chat_id}")

        # Update the chat with the generated title
        await app.chat_history_manager.update_chat_name(chat_id, title)
        logger.info(f"Updated chat {chat_id} title to: {title}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "title": title,
                "message": "Chat title generated and updated successfully",
            },
        )
    except Exception as e:
        logger.error(f"Error updating chat title: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat title: {str(e)}",
        )


@app.post("/chat")
async def chat(chat_request: ChatRequest):
    evaluation_client = EvaluationClient(app.settings)

    try:
        generation_client = GenerationClient(
            settings=app.settings,
            provider=chat_request.provider,
        )
        logger.info(f"Generation client created with provider: {chat_request.provider}")
    except Exception as e:
        logger.error(f"Failed to create generation client: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Internal server error: {str(e)}"},
        )

    document_id = chat_request.document_id
    logger.info(f"Looking for chat with document_id: {document_id}")

    # Get chat info by document_id to retrieve the chat_id
    chat_info = await app.chat_history_manager.get_chat_by_document_id(document_id)
    logger.info(f"chat_info result: {chat_info}")
    if not chat_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Chat not found for this document"},
        )

    chat_id = chat_info.get("id")
    if not chat_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid chat data"},
        )

    history = await app.chat_history_manager.get_chat_history_for_llm(chat_id)

    controller = Controller(
        embedding_client=app.embedding_client,
        vdb_client=app.vdb_client,
        generation_client=generation_client,
        advancedrag_client=app.advanced_rag_client,
        tts_client=app.tts_client,
        chat_history_manager=app.chat_history_manager,
        document_id=document_id,
        eval_client=evaluation_client,
    )

    if app.settings.STREAMING:
        return await handle_streaming_response(
            chat_request, controller, history, chat_id
        )
    else:
        return await handle_non_streaming_response(
            chat_request, controller, history, chat_id
        )


async def handle_streaming_response(
    chat_request: ChatRequest, controller: Controller, history, chat_id: int
):
    async def stream_generator():
        full_answer = ""
        retrieved_results = None
        try:
            async for event_type, data in controller.answer_stream(
                document_id=controller.document_id,
                query=chat_request.query,
                chat_history=history,
                filter=app.settings.FILTER,
                split=app.settings.SPLIT,
                limit=6,
            ):
                if event_type == "text":
                    full_answer += data
                    yield json.dumps({"type": "text", "content": data})
                elif event_type == "chunks":
                    retrieved_results = data
                    yield json.dumps({"type": "chunks", "content": data})
        except Exception as e:
            logger.error(f"Error in streaming: {str(e)}", exc_info=True)
            yield json.dumps({"error": f"Streaming error: {str(e)}"})
            return

        if chat_request.generate_audio and full_answer:
            audio_file = await generate_audio_response(controller, full_answer)
            if audio_file:
                yield json.dumps({"type": "audio", "content": str(audio_file)})

        try:
            await app.chat_history_manager.add_message(
                chat_id=chat_id, role="user", content=chat_request.query
            )
            logger.info(f"Added user message to chat {chat_id}")
            await app.chat_history_manager.add_message(
                chat_id=chat_id, role="assistant", content=full_answer
            )
            logger.info(f"Added assistant message to chat {chat_id}")
        except Exception as e:
            logger.error(f"Error saving chat messages: {str(e)}")

        asyncio.create_task(
            run_evaluation(
                controller, chat_request.query, full_answer, retrieved_results
            )
        )

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


async def handle_non_streaming_response(
    chat_request: ChatRequest, controller: Controller, history, chat_id: int
):
    answer, chunks = await controller.answer(
        document_id=controller.document_id,
        query=chat_request.query,
        chat_history=history,
        filter=app.settings.FILTER,
        split=app.settings.SPLIT,
        limit=6,
    )

    if not answer:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to generate answer"},
        )

    try:
        await app.chat_history_manager.add_message(
            chat_id=chat_id, role="user", content=chat_request.query
        )
        await app.chat_history_manager.add_message(
            chat_id=chat_id, role="assistant", content=answer
        )
    except Exception as e:
        logger.error(f"Error saving chat messages: {str(e)}")

    audio_file = None
    if chat_request.generate_audio:
        logger.info("Generating audio...")
        audio_file = await generate_audio_response(controller, answer)
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


async def generate_audio_response(controller: Controller, text: str):
    try:
        response_index = app.audio_response_counter
        app.audio_response_counter += 1
        return await controller.generate_audio(text, response_index)
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}", exc_info=True)
        return None


async def run_evaluation(
    controller: Controller, query: str, answer: str, retrieved_results
):
    try:
        answer_relevancy, faithfulness = await controller.evaluate_answer(
            query, answer, retrieved_results
        )
        logger.info(
            "Answer relevancy (how relevant a response is to the user input): {}".format(
                answer_relevancy
            )
        )
        logger.info(
            "Faithfulness (how accurately a response reflects the retrieved documents): {}".format(
                faithfulness
            )
        )
    except Exception as e:
        error_msg = str(e)
        if "max_tokens" in error_msg or "IncompleteOutputException" in error_msg:
            logger.warning("Evaluation skipped due to response length limit")
        else:
            logger.error(f"Error in background evaluation: {error_msg}")


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve audio files from the voices directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
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
