import axios from 'axios';
import { ChatRequest, ChatResponse, UploadResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://0.0.0.0:80';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadFile = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<UploadResponse>('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const sendChatMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  const response = await apiClient.post<ChatResponse>('/chat', request);
  return response.data;
};

export interface StreamChunk {
  type: 'text' | 'chunks' | 'audio';
  content: string | string[];
}

export const sendChatMessageStream = async (
  request: ChatRequest,
  onChunk: (chunk: StreamChunk) => void,
): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No reader available');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') {
          return;
        }
        try {
          const chunk = JSON.parse(data) as StreamChunk;
          onChunk(chunk);
        } catch (e) {
          console.error('Failed to parse chunk:', data, e);
        }
      }
    }
  }
};

export const getAudioUrl = (audioPath: string): string => {
  if (!audioPath) return '';
  const filename = audioPath.split('/').pop() || audioPath;
  return `${API_BASE_URL}/audio/${filename}`;
};
