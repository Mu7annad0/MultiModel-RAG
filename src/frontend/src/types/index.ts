export interface UploadResponse {
  message: string;
  document_id: string;
  filename: string;
  chat_id: number;
}

export interface ChatRequest {
  document_id: string;
  query: string;
  provider: 'openai' | 'gemini' | 'deepseek';
  generate_audio: boolean;
}

export interface ChatResponse {
  answer: string;
  chunks: string[] | null;
  audio_file: string | null;
}

export type ModelProvider = 'openai' | 'gemini' | 'deepseek';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  chunks?: string[];
  audio_file?: string | null;
  streaming_complete?: boolean;
  timestamp: number;
  reasoning?: string[];
}

export interface FileUploadState {
  file: File | null;
  isUploading: boolean;
  progress: number;
  error: string | null;
  documentId: string | null;
  savedFileSize: number | null;
  status: 'idle' | 'uploading' | 'indexing' | 'ready' | 'error';
}

export interface Chat {
  id: number;
  chat_name: string;
  created_at: string;
  updated_at: string;
  document_id: string | null;
  filename?: string | null;
}

export interface NewChatResponse {
  chat_id: number;
  chat_name: string;
  message: string;
}

export interface ChatListResponse {
  chats: Chat[];
}

export interface ChatMessagesResponse {
  chat: Chat;
  messages: Array<{
    id: number;
    role: string;
    content: string;
    created_at: string;
  }>;
}
