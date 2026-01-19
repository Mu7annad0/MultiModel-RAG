import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, ChevronDown, Volume2, Check } from 'lucide-react';
import { ModelProvider } from '../types';
import openaiIcon from '../../icons/openai_icon.png';
import geminiIcon from '../../icons/gemini_icon.png';
import deepseekIcon from '../../icons/deepseek_icon.png';

interface ChatInputProps {
  onSendMessage: (query: string) => Promise<void>;
  disabled?: boolean;
  isLoading?: boolean;
  selectedModel: ModelProvider;
  generateAudio: boolean;
  onModelChange: (model: ModelProvider) => void;
  onAudioChange: (enabled: boolean) => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled,
  isLoading,
  selectedModel,
  generateAudio,
  onModelChange,
  onAudioChange,
}) => {
  const [input, setInput] = useState('');
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const [inputHeight, setInputHeight] = useState('32px');
  
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const models: { id: ModelProvider; label: string; icon: string }[] = [
    { id: 'openai', label: 'OpenAI', icon: openaiIcon },
    { id: 'gemini', label: 'Gemini', icon: geminiIcon },
    { id: 'deepseek', label: 'DeepSeek', icon: deepseekIcon },
  ];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsModelDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || disabled) return;

    const query = input.trim();
    setInput('');
    setInputHeight('32px');

    try {
      await onSendMessage(query);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInput(value);
    
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
      setInputHeight(`${inputRef.current.scrollHeight}px`);
    }
  };

  const handleModelSelect = (model: ModelProvider) => {
    onModelChange(model);
    setIsModelDropdownOpen(false);
  };

  const currentModelLabel = models.find(m => m.id === selectedModel)?.label || 'OpenAI';

  const isDisabled = disabled || isLoading;
  const hasInput = input.trim().length > 0;

  return (
    <div className="bg-card border-t border-border">
      <form onSubmit={handleSubmit} className="flex items-end px-3 py-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? 'Upload a PDF first...' : 'Ask about your document...'}
          disabled={isDisabled}
          rows={1}
          className="flex-1 px-3 py-1.5 bg-transparent border-none resize-none 
            focus:outline-none focus:ring-0
            disabled:opacity-50 disabled:cursor-not-allowed
            placeholder:text-muted-foreground text-sm overflow-hidden"
          style={{
            minHeight: '32px',
            height: inputHeight,
          }}
        />

        <div className="flex items-center gap-2 ml-3 flex-shrink-0" ref={dropdownRef}>
          <div className="relative">
            <button
              type="button"
              onClick={() => !isDisabled && setIsModelDropdownOpen(!isModelDropdownOpen)}
              disabled={isDisabled}
              className={`
                flex items-center gap-1.5 px-3 py-2 border border-border rounded-full
                transition-all duration-200
                ${isDisabled 
                  ? 'text-muted-foreground cursor-not-allowed opacity-50' 
                  : 'text-foreground hover:border-primary hover:text-primary cursor-pointer'
                }
              `}
            >
              <img
                src={models.find(m => m.id === selectedModel)?.icon}
                alt={currentModelLabel}
                className="w-4 h-4 rounded-sm object-contain"
              />
              <span className="text-xs font-medium">{currentModelLabel}</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isModelDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {isModelDropdownOpen && (
              <div className="absolute bottom-full right-0 mb-1 w-36 bg-card border border-border rounded-lg shadow-lg overflow-hidden z-50">
                {models.map((model) => (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => handleModelSelect(model.id)}
                    className={`
                      w-full flex items-center justify-between px-3 py-2 text-xs
                      hover:bg-secondary/50 transition-colors cursor-pointer
                      ${selectedModel === model.id ? 'text-primary bg-primary/5' : 'text-foreground'}
                    `}
                  >
                    <div className="flex items-center gap-2">
                      <img
                        src={model.icon}
                        alt={model.label}
                        className="w-4 h-4 rounded-sm object-contain"
                      />
                      <span>{model.label}</span>
                    </div>
                    {selectedModel === model.id && <Check className="w-3 h-3" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => !isDisabled && onAudioChange(!generateAudio)}
            disabled={isDisabled}
            className={`
              flex items-center gap-1.5 px-3 py-2 border border-border rounded-full
              transition-all duration-200
              ${generateAudio 
                ? 'bg-primary text-white border-primary' 
                : 'text-muted-foreground hover:border-primary hover:text-primary'
              }
              ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
            title="Generate Audio"
          >
            <Volume2 className="w-4 h-4" />
            <span className="text-xs font-medium">Audio Response</span>
          </button>

          <button
            type="submit"
            disabled={isDisabled || !hasInput}
            className={`
              flex items-center justify-center p-2 border border-border rounded-full
              transition-all duration-200
              ${hasInput && !isDisabled
                ? 'bg-black dark:bg-white text-white dark:text-black border-border hover:border-primary cursor-pointer' 
                : 'text-muted-foreground cursor-not-allowed'
              }
            `}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
