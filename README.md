# Multi-Model PDF RAG Assistant with Audio

A powerful Retrieval-Augmented Generation (RAG) system featuring intelligent query decomposition and semantic chunk filtering. Upload PDF documents, query their content using different LLM providers, and receive responses with audio playback and transparent source citations.

## Features

- **PDF Document Processing**: Upload and process PDF documents up to 100 pages with automatic text extraction and intelligent chunking
- **Multi-Model Support**: Switch between GPT-5, Gemini-3-Pro, and DeepSeek-R1
- **Advanced RAG**: 
  - Query decomposition for complex multi-part questions
  - LLM-based chunk filtering to remove irrelevant passages
- **RAG Evaluation**: Automatic assessment of response quality using Ragas metrics:
  - **Answer Relevancy**: Measures how relevant the response is to the user query
  - **Faithfulness**: Evaluates how accurately the response reflects the retrieved documents
- **Source Citations**: Display exact text chunks used to generate each answer for full transparency
- **Text-to-Speech Audio**: Convert AI responses to natural-sounding audio using OpenAI TTS
- **Streaming Responses**: Real-time streaming of AI responses for improved UX
- **Multi-Chat Management**: Create, delete, and switch between multiple chat sessions
- **Chat History Persistence**: Stores conversation history and chat metadata in PostgreSQL database
- **Auto-Generated Chat Titles**: Automatically generates descriptive titles based on the first message
- **Modern UI**: Responsive React interface with dark mode, glassmorphism effects, and smooth animations
<br><br>
![Demo](images/demo.png)

## Tech Stack

### Backend
- **FastAPI**: High-performance async API framework for Python
- **LangChain**: Document processing and text splitting
- **Qdrant**: Vector database for similarity search and storage
- **PostgreSQL**: Database for persistent chat history and metadata storage
- **Ragas**: RAG evaluation framework for answer relevancy and faithfulness metrics
- **OpenAI SDK**: GPT models and DeepSeek integration (OpenAI-compatible)
- **Google GenAI**: Gemini model integration
- **Cohere**: Alternative embedding provider

### Frontend
- **React 18**: Component-based UI framework
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Vite**: Fast build tool and dev server
- **WaveSurfer.js**: Audio waveform visualization
- **Lucide React**: Icon library

## Project Structure

```
MultiModel-RAG/
├── src/
│   ├── backend/
│   │   ├── main.py                      # FastAPI application entry point
│   │   ├── cfg.py                       # Settings configuration with pydantic-settings
│   │   ├── controller.py                # Core business logic and RAG operations
│   │   ├── prompts.py                   # Prompt templates for LLM and RAG
│   │   ├── chat_history.py              # Chat history persistence manager
│   │   ├── logging.py                   # Logging configuration
│   │   └── clients/
│   │       ├── __init__.py              # Client exports
│   │       ├── embedding.py             # Multi-provider embedding client (OpenAI, Gemini, Cohere)
│   │       ├── vdb.py                   # Qdrant vector database client
│   │       ├── llms.py                  # LLM generation and AdvancedRAG clients
│   │       ├── tts.py                   # Text-to-speech client
│   │       ├── eval.py                  # RAG evaluation client using Ragas
│   │       └── llm_providers/
│   │           ├── __init__.py
│   │           ├── llm_interface.py     # Abstract LLM provider interface
│   │           └── providers.py         # Gemini, OpenAI, DeepSeek implementations
│   ├── frontend/                        # React frontend application
│   ├── pyproject.toml                   # Python project configuration
│   ├── .env                             # Environment variables (create from .env.example)
│   └── README.md
```

## API Endpoints

### POST /upload
Upload a PDF document for processing.

**Request**: `multipart/form-data` with `file` field

**Response**:
```json
{
  "document_id": "uuid-string"
}
```

### POST /chat
Query the uploaded document.

**Request**:
```json
{
  "document_id": "uuid-string",
  "query": "What are the main findings?",
  "provider": "openai | gemini | deepseek",
  "generate_audio": true
}
```

**Response**:
```json
{
  "answer": "Based on the document...",
  "chunks": ["In Page 1: \"chunk text...\"", "In Page 2: \"chunk text...\""]，
  "audio_file": "/audio/speech_response_1.mp3"
}
```

## Installation

### Prerequisites
- Python 3.10 or higher
- Node.js 18+ and npm
- API keys for desired LLM providers (OpenAI, Google, DeepSeek)

### Backend Setup

1. Create virtual environment and install dependencies:
```bash
uv venv mm_rag
source mm_rag/bin/activate
uv sync
```

2. Configure environment variables:
```bash
cp .env.example .env    # Edit .env with your API keys
```

### Frontend Setup

```bash
cd src/frontend
npm install
```

## Running the Project

### Start the Backend Server

```bash
cd src/backend
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 80
```

The API will be available at `http://localhost:80`

### Start the Frontend Development Server

```bash
cd src/frontend
npm run dev
```

The UI will be available at `http://localhost:3000`

## Environment Variables

Create a `.env` file in `src/` with the following configuration:

```env
# LLM API Keys
OPENAI_API_KEY=sk-your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
COHERE_API_KEY=your_cohere_api_key

# Embedding Configuration
EMBEDDING_PROVIDER=openai  # openai, gemini, or cohere
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
GEMINI_EMBEDDING_MODEL=embedding-001
COHERE_EMBEDDING_MODEL=embed-english-v3.0
EMBEDDING_DIMENSION=1024

# Model IDs
OPENAI_MODEL_ID=gpt-4o-mini
GEMINI_MODEL_ID=gemini-1.5-flash
DEEPSEEK_MODEL_ID=deepseek/deepseek-r1-0528:free
EVALUATION_MODEL=gpt-4o-mini  # Model for RAG evaluation

# RAG Configuration
FILTER=true           # Enable chunk filtering
SPLIT=true            # Enable query decomposition
STREAMING=true        # Enable streaming responses

# File Upload Limits
FILE_PAGES=100
FILE_FORMATS=["application/pdf"]
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Database
DB_DIR=../assets/database/qdrant_db

# PostgreSQL Database (for chat history persistence)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/mmrag
```

## Usage Guide

1. **Start the Application**: Run both backend and frontend servers
2. **Create a New Chat**: Click "New Chat" button in the sidebar
3. **Upload a Document**: Click the paperclip icon in the chat input to upload a PDF (max 100 pages)
4. **Select Model**: Choose your preferred LLM from the dropdown selector
5. **Enable Audio**: Toggle the audio button to hear responses read aloud
6. **Ask Questions**: Type queries about the document content in the chat interface
7. **View Sources**: Expand the source chunks below each answer to see citations
8. **Manage Chats**: Switch between chats from the sidebar, or delete unwanted chats by hovering and clicking the trash icon
