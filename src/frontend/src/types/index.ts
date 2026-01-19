export interface UploadResponse {
  message: string;
  document_id: string;
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
}

export interface FileUploadState {
  file: File | null;
  isUploading: boolean;
  progress: number;
  error: string | null;
  documentId: string | null;
  savedFileSize: number | null;
}
