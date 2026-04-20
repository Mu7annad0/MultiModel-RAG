import React, { useState, useEffect } from 'react';
import { Brain, ChevronDown, ChevronUp } from 'lucide-react';

interface ReasoningBlockProps {
  reasoning: string[];
  isStreaming?: boolean;
}

export const ReasoningBlock: React.FC<ReasoningBlockProps> = ({ 
  reasoning, 
  isStreaming = false 
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [dots, setDots] = useState('');
  
  useEffect(() => {
    if (!isStreaming) {
      setDots('');
      return;
    }
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 400);
    return () => clearInterval(interval);
  }, [isStreaming]);
  
  if (!reasoning || reasoning.length === 0) return null;

  const filteredReasoning = reasoning.filter(
    step => !step.match(/^Found \d+ relevant chunks?$/i)
  );

  if (filteredReasoning.length === 0) return null;

  return (
    <div className="mb-3 rounded-lg border border-primary/20 dark:border-primary/40 bg-primary/5 dark:bg-primary/10 overflow-hidden">
      {/* Header with toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-primary/10 dark:hover:bg-primary/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary animate-pulse" />
          <span className="text-xs font-medium text-primary">
            Reasoning{isStreaming && <span className="ml-1">{dots}</span>}
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-primary" />
        ) : (
          <ChevronDown className="w-4 h-4 text-primary" />
        )}
      </button>
      
      {/* Reasoning content */}
      {isExpanded && (
        <div className="px-3 pb-3">
          <p className="text-xs text-foreground/80 leading-relaxed">
            {filteredReasoning.join(' ')}
            {isStreaming && (
              <span className="inline-block w-1.5 h-3 ml-0.5 bg-primary align-middle animate-pulse"></span>
            )}
          </p>
        </div>
      )}
    </div>
  );
};
