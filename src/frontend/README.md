# Multi-Model PDF RAG Assistant - Frontend

A modern, production-ready React frontend for the Multi-Model PDF RAG Assistant with Audio support.

## Tech Stack

- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite 5
- **Styling:** Tailwind CSS 3.4
- **UI Components:** Custom Shadcn/UI-style components
- **Icons:** Lucide React
- **HTTP Client:** Axios
- **Theme:** Dark mode (default)

## Project Structure

```
src/frontend/
├── src/
│   ├── components/
│   │   ├── FileUpload.tsx         # PDF upload with drag & drop
│   │   ├── ChatWindow.tsx         # Main chat interface
│   │   ├── MessageBubble.tsx      # Chat message bubbles
│   │   ├── AudioPlayer.tsx        # Audio playback component
│   │   ├── AudioToggle.tsx        # Model selector & audio toggle
│   │   ├── SourceChunksAccordion.tsx  # Source citations accordion
│   │   └── index.ts               # Component exports
│   ├── services/
│   │   └── api.ts                 # API integration layer
│   ├── types/
│   │   └── index.ts               # TypeScript types & interfaces
│   ├── App.tsx                    # Main application component
│   ├── main.tsx                   # Entry point
│   ├── index.css                  # Global styles & Tailwind
│   └── vite-env.d.ts              # Vite type definitions
├── index.html                     # HTML template
├── package.json                   # Dependencies
├── vite.config.ts                 # Vite configuration
├── tailwind.config.js             # Tailwind CSS configuration
├── tsconfig.json                  # TypeScript configuration
└── README.md                      # This file
```

## Features

- **PDF Upload:** Drag & drop or file picker with progress indicator
- **Multi-Model Support:** Toggle between OpenAI, Gemini, and DeepSeek
- **Audio Generation:** Optional text-to-speech responses
- **Chat Interface:** Modern chat UI with loading states
- **Source Citations:** Collapsible accordion showing source chunks
- **Error Handling:** Clear error messages for users
- **Dark Mode:** Dark theme by default with smooth transitions
- **Responsive:** Desktop-first design with mobile support

## API Integration

### Backend Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload PDF file (multipart/form-data) |
| `/chat` | POST | Send chat query (JSON) |

### API Contract

**Upload Response:**
```json
{
  "message": "Document indexed successfully",
  "document_id": "uuid-string"
}
```

**Chat Request:**
```json
{
  "document_id": "string",
  "query": "string",
  "provider": "openai" | "gemini" | "deepseek",
  "generate_audio": boolean
}
```

**Chat Response:**
```json
{
  "answer": "string",
  "chunks": ["source chunk text...", "..."],
  "audio_file": "path-or-null"
}
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd src/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser to `http://localhost:3000`

### Running with Backend

The Vite dev server is configured with proxy to forward API requests to `http://0.0.0.0:80` (the FastAPI backend).

Make sure the backend is running:
```bash
# From the project root
uv run src/main.py
```

### Production Build

```bash
npm run build
```

The build output will be in the `dist` directory.

## Environment Variables

Create a `.env` file in the `src/frontend` directory:

```env
VITE_API_URL=http://0.0.0.0:80
```

## Styling

The frontend uses Tailwind CSS with a custom color palette matching Shadcn/UI design principles. Key design elements:

- **Border Radius:** 0.75rem (lg), 0.5rem (md), 0.25rem (sm)
- **Colors:** HSL-based CSS variables for easy theming
- **Animations:** Custom fade-in, slide-in, and accordion animations
- **Glassmorphism:** Subtle transparency effects on cards

## Component Highlights

### FileUpload
- Drag & drop zone with visual feedback
- File type validation (PDF only)
- Upload progress indicator
- Success/error states

### ChatWindow
- Auto-scrolling to newest messages
- Loading state animation
- Auto-resizing textarea input
- Keyboard shortcut (Enter to send)

### SourceChunksAccordion
- Smooth expand/collapse animation
- Numbered source chunks
- Visual quote indicator

## License

MIT
