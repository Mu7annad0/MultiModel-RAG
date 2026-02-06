import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot, Loader2 } from 'lucide-react';
import { AudioPlayer } from './AudioPlayer';
import { SourceChunksAccordion } from './SourceChunksAccordion';
import { Message } from '../types';

interface MessageBubbleProps {
  message: Message;
  isLoading?: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ 
  message, 
  isLoading 
}) => {
  const isUser = message.role === 'user';

  console.log('MessageBubble render:', { id: message.id, role: message.role, isLoading, content: message.content, audio_file: message.audio_file, streaming_complete: message.streaming_complete });

  const showLoading = isLoading && !message.audio_file;
  const showAudioPlaceholder = !isUser && message.audio_file && !message.content && message.streaming_complete;
  const showEmptyState = !isUser && !message.content && !message.audio_file && message.streaming_complete;

  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`
        flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium
        ${isUser 
          ? 'bg-primary text-primary-foreground' 
          : 'bg-secondary text-secondary-foreground'
        }
      `}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className={`
        max-w-[75%] rounded-xl px-3 py-2
        ${isUser 
          ? 'bg-primary text-primary-foreground dark:text-black rounded-tr-sm' 
          : 'bg-card text-card-foreground border border-border rounded-tl-sm'
        }
        shadow-sm
      `}>
        {showLoading ? (
          <div className="flex items-center gap-2">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span className="text-xs">Thinking...</span>
          </div>
        ) : (
          <>
            {message.content ? (
              <div className={`text-sm leading-relaxed prose prose-sm dark:prose-invert max-w-none ${isUser ? 'text-primary-foreground dark:text-black' : ''}`}>
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            ) : showAudioPlaceholder ? (
              <div className="text-xs text-muted-foreground italic">
                Audio response
              </div>
            ) : showEmptyState ? (
              <div className="text-xs text-muted-foreground italic">
                No response generated
              </div>
            ) : null}

            {!isUser && (
              <>
                <AudioPlayer audioFile={message.audio_file} />
                <SourceChunksAccordion chunks={message.chunks} />
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};
