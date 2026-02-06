import axios from 'axios';
import { ChatRequest, ChatResponse, UploadResponse, NewChatResponse, ChatListResponse, ChatMessagesResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://0.0.0.0:80';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Chat Management APIs
export const createNewChat = async (firstMessage: string = '', documentId?: string): Promise<NewChatResponse> => {
  const response = await apiClient.post<NewChatResponse>('/new_chat', {
    first_message: firstMessage,
    document_id: documentId,
  });
  return response.data;
};

export const listChats = async (): Promise<ChatListResponse> => {
  const response = await apiClient.get<ChatListResponse>('/chats');
  return response.data;
};

export const getChatMessages = async (chatId: number): Promise<ChatMessagesResponse> => {
  const response = await apiClient.get<ChatMessagesResponse>(`/chats/${chatId}/messages`);
  return response.data;
};

export const deleteChat = async (chatId: number): Promise<void> => {
  await apiClient.delete(`/chats/${chatId}`);
};

export const updateChatTitle = async (chatId: number, message: string): Promise<{ title: string; message: string }> => {
  const response = await apiClient.patch<{ title: string; message: string }>(`/chats/${chatId}`, {
    message,
  });
  return response.data;
};

// File Upload API
export const uploadFile = async (file: File, chatId?: number): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const url = chatId ? `/upload?chat_id=${chatId}` : '/upload';
  const response = await apiClient.post<UploadResponse>(url, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

// Chat Message APIs
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
