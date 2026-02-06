import React, { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { Message, ModelProvider } from '../types';

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (query: string) => Promise<void>;
  disabled?: boolean;
  selectedModel?: ModelProvider;
  generateAudio?: boolean;
  onModelChange?: (model: ModelProvider) => void;
  onAudioChange?: (enabled: boolean) => void;
  onUploadClick: () => void;
  fileStatus: 'none' | 'uploading' | 'indexing' | 'ready' | 'error';
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  isLoading,
  onSendMessage,
  disabled,
  selectedModel = 'openai',
  generateAudio = false,
  onModelChange = () => {},
  onAudioChange = () => {},
  onUploadClick,
  fileStatus,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-3">
              <div className="w-14 h-14 mx-auto rounded-full bg-secondary flex items-center justify-center">
                <svg
                  className="w-7 h-7 text-muted-foreground"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
              </div>
              <div>
                <p className="text-base font-medium text-foreground">
                  Start a conversation
                </p>
                <p className="text-xs text-muted-foreground">
                  {disabled 
                    ? 'Upload a PDF to start chatting' 
                    : 'Ask questions about your uploaded PDF'}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                isLoading={isLoading && message.role === 'assistant' && !message.content && !message.audio_file && !message.streaming_complete}
              />
            ))}
            {isLoading && messages[messages.length - 1]?.role === 'user' && (
              <MessageBubble
                message={{
                  id: 'loading',
                  role: 'assistant',
                  content: '',
                  timestamp: Date.now(),
                }}
                isLoading
              />
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <ChatInput
        onSendMessage={onSendMessage}
        disabled={disabled}
        isLoading={isLoading}
        selectedModel={selectedModel}
        generateAudio={generateAudio}
        onModelChange={onModelChange}
        onAudioChange={onAudioChange}
        onUploadClick={onUploadClick}
        fileStatus={fileStatus}
      />
    </div>
  );
};
