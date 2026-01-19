import React from 'react';
import { Volume2, VolumeX } from 'lucide-react';

interface AudioToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  disabled?: boolean;
}

export const AudioToggle: React.FC<AudioToggleProps> = ({ 
  enabled, 
  onChange, 
  disabled 
}) => {
  return (
    <button
      onClick={() => !disabled && onChange(!enabled)}
      disabled={disabled}
      className={`
        flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200
        ${enabled 
          ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/25' 
          : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {enabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
      <span className="text-sm">🔊 Generate Audio</span>
    </button>
  );
};

interface ModelSelectorProps {
  selected: 'openai' | 'gemini' | 'deepseek';
  onChange: (model: 'openai' | 'gemini' | 'deepseek') => void;
  disabled?: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({ 
  selected, 
  onChange, 
  disabled 
}) => {
  const models = [
    { id: 'openai' as const, label: 'OpenAI' },
    { id: 'gemini' as const, label: 'Gemini' },
    { id: 'deepseek' as const, label: 'DeepSeek' },
  ];

  return (
    <div className="flex items-center gap-1 p-1 rounded-lg bg-secondary">
      {models.map((model) => (
        <button
          key={model.id}
          onClick={() => !disabled && onChange(model.id)}
          disabled={disabled}
          className={`
            px-4 py-2 rounded-md text-sm font-medium transition-all duration-200
            ${selected === model.id 
              ? 'bg-background text-foreground shadow-sm' 
              : 'text-muted-foreground hover:text-foreground'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          {model.label}
        </button>
      ))}
    </div>
  );
};
