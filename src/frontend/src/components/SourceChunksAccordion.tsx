import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Quote } from 'lucide-react';

interface SourceChunksAccordionProps {
  chunks: string[] | undefined;
}

export const SourceChunksAccordion: React.FC<SourceChunksAccordionProps> = ({ chunks }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!chunks || chunks.length === 0) return null;

  return (
    <div className="mt-2 border border-border rounded-lg overflow-hidden animate-fade-in">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-2 bg-secondary/30 hover:bg-secondary/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Quote className="w-3 h-3 text-muted-foreground" />
          <span className="text-xs font-medium text-muted-foreground">
            Sources ({chunks.length})
          </span>
        </div>
        {isOpen ? (
          <ChevronUp className="w-3 h-3 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-3 h-3 text-muted-foreground" />
        )}
      </button>

      {isOpen && (
        <div className="animate-accordion-down">
          {chunks.map((chunk, index) => (
            <div
              key={index}
              className="p-2 border-t border-border"
            >
              <div className="flex items-start gap-2">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-xs font-medium flex items-center justify-center">
                  {index + 1}
                </span>
                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                  {chunk}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
