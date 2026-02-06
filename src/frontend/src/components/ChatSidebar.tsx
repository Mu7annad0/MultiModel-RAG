import React, { useState } from 'react';
import { Trash2, MessageSquare, Plus } from 'lucide-react';

export interface Chat {
  id: number;
  chat_name: string;
  created_at: string;
  updated_at: string;
  document_id: string | null;
}

interface ChatSidebarProps {
  chats: Chat[];
  activeChatId: number | null;
  onSelectChat: (chatId: number) => void;
  onCreateChat: () => void;
  onDeleteChat: (chatId: number) => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  chats,
  activeChatId,
  onSelectChat,
  onCreateChat,
  onDeleteChat,
}) => {
  const [hoveredChatId, setHoveredChatId] = useState<number | null>(null);

  return (
    <aside className="w-72 flex-shrink-0 flex flex-col bg-card border-r border-border h-full transition-colors duration-300 ease-in-out">
      <div className="p-4 border-b border-border transition-colors duration-300 ease-in-out">
        <button
          onClick={onCreateChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-all duration-300 ease-in-out font-medium text-sm"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {chats.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground transition-colors duration-300 ease-in-out">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50 transition-colors duration-300 ease-in-out" />
            <p className="text-sm transition-colors duration-300 ease-in-out">No chats yet</p>
            <p className="text-xs mt-1 transition-colors duration-300 ease-in-out">Create a new chat to get started</p>
          </div>
        ) : (
          chats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => onSelectChat(chat.id)}
              onMouseEnter={() => setHoveredChatId(chat.id)}
              onMouseLeave={() => setHoveredChatId(null)}
              className={`
                group flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer
                transition-all duration-300 ease-in-out
                ${activeChatId === chat.id
                  ? 'bg-primary/10 border border-primary/20'
                  : 'hover:bg-secondary border border-transparent'
                }
              `}
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <MessageSquare className="w-4 h-4 text-muted-foreground flex-shrink-0 transition-colors duration-300 ease-in-out" />
                <span className="text-sm truncate text-foreground transition-colors duration-300 ease-in-out">
                  {chat.chat_name}
                </span>
              </div>
              
              {hoveredChatId === chat.id && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteChat(chat.id);
                  }}
                  className="p-1.5 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-all duration-300 ease-in-out flex-shrink-0"
                  title="Delete chat"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </aside>
  );
};
