import { useState, useCallback, useEffect, useMemo } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { ChatSidebar } from './components/ChatSidebar';
import { FileUploadModal } from './components/FileUploadModal';
import { sendChatMessage, sendChatMessageStream, StreamChunk, createNewChat, listChats, getChatMessages, deleteChat, updateChatTitle } from './services/api';
import { Message, ModelProvider, Chat } from './types';
import { Sun, Moon, PanelLeftClose, PanelLeft } from 'lucide-react';

// File status per chat
interface ChatFileState {
  documentId: string | null;
  filename: string | null;
  status: 'none' | 'uploading' | 'indexing' | 'ready' | 'error';
}

function App() {
  // Chat management state
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  
  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  // File state per chat
  const [chatFiles, setChatFiles] = useState<Map<number, ChatFileState>>(new Map());
  
  // UI state
  const [selectedModel, setSelectedModel] = useState<ModelProvider>('openai');
  const [generateAudio, setGenerateAudio] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // Theme handling
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  // Load chats on mount
  useEffect(() => {
    loadChats();
  }, []);

  const loadChats = async () => {
    try {
      const response = await listChats();
      setChats(response.chats);
      
      // Restore file states from localStorage
      const savedFiles = localStorage.getItem('chat_files');
      if (savedFiles) {
        const parsed = JSON.parse(savedFiles);
        setChatFiles(new Map(parsed));
      }
    } catch (error) {
      console.error('Failed to load chats:', error);
    }
  };

  // Save chat files to localStorage whenever they change
  useEffect(() => {
    if (chatFiles.size > 0) {
      localStorage.setItem('chat_files', JSON.stringify(Array.from(chatFiles.entries())));
    }
  }, [chatFiles]);

  const currentFileState = useMemo(() => {
    if (!activeChatId) return { status: 'none' as const, documentId: null, filename: null };
    return chatFiles.get(activeChatId) || { status: 'none' as const, documentId: null, filename: null };
  }, [chatFiles, activeChatId]);

  const handleCreateChat = useCallback(async () => {
    try {
      const response = await createNewChat();
      const newChat: Chat = {
        id: response.chat_id,
        chat_name: response.chat_name,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        document_id: null,
      };
      setChats(prev => [newChat, ...prev]);
      setActiveChatId(newChat.id);
      setMessages([]);
      
      // Initialize file state for new chat
      setChatFiles(prev => new Map(prev.set(newChat.id, {
        documentId: null,
        filename: null,
        status: 'none',
      })));
    } catch (error) {
      console.error('Failed to create chat:', error);
    }
  }, []);

  const handleSelectChat = useCallback(async (chatId: number) => {
    if (chatId === activeChatId) return;
    
    setActiveChatId(chatId);
    setIsLoading(false);
    
    try {
      const response = await getChatMessages(chatId);
      
      // Convert backend messages to frontend format
      const formattedMessages: Message[] = response.messages.map((msg, index) => ({
        id: msg.id.toString() || index.toString(),
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.created_at).getTime(),
        streaming_complete: true,
      }));
      
      setMessages(formattedMessages);
      
      // Restore file state from chat data
      if (response.chat.document_id) {
        setChatFiles(prev => {
          const existing = prev.get(chatId);
          return new Map(prev.set(chatId, {
            documentId: response.chat.document_id,
            filename: existing?.filename || null,
            status: 'ready',
          }));
        });
      }
    } catch (error) {
      console.error('Failed to load chat messages:', error);
      setMessages([]);
    }
  }, [activeChatId]);

  const handleDeleteChat = useCallback(async (chatId: number) => {
    try {
      await deleteChat(chatId);
      setChats(prev => prev.filter(chat => chat.id !== chatId));
      
      // Remove file state
      setChatFiles(prev => {
        const next = new Map(prev);
        next.delete(chatId);
        return next;
      });
      
      // If we deleted the active chat, clear it
      if (activeChatId === chatId) {
        setActiveChatId(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
    }
  }, [activeChatId]);

  const handleUploadSuccess = useCallback((documentId: string, chatId: number, filename: string) => {
    // Update file state for the chat
    setChatFiles(prev => new Map(prev.set(chatId, {
      documentId,
      filename,
      status: 'ready',
    })));
    
    // Update chat in list with document_id
    setChats(prev => prev.map(chat => 
      chat.id === chatId 
        ? { ...chat, document_id: documentId }
        : chat
    ));
    
    // If this is a new chat from upload, set it as active
    if (chatId !== activeChatId) {
      setActiveChatId(chatId);
      setMessages([]);
      // Reload chats to get the new one
      loadChats();
    }
  }, [activeChatId]);

  const handleUploadError = useCallback((error: string) => {
    console.error('Upload error:', error);
    // Keep the upload modal open to show the error
  }, []);

  const handleOpenUploadModal = useCallback(() => {
    setIsUploadModalOpen(true);
  }, []);

    const handleSendMessage = useCallback(async (query: string) => {
    if (!currentFileState.documentId || !activeChatId) return;

    // Check if this is the first user message (chat still has default name)
    const currentChat = chats.find(chat => chat.id === activeChatId);
    const isFirstMessage = currentChat?.chat_name.toLowerCase() === 'new chat';

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    const assistantMessageId = (Date.now() + 1).toString();

    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      chunks: [],
      streaming_complete: false,
      timestamp: Date.now() + 1,
    };
    setMessages(prev => [...prev, assistantMessage]);

    // Update chat title in the background (don't block the chat)
    if (isFirstMessage) {
      updateChatTitle(activeChatId, query)
        .then(titleResponse => {
          // Update the chat name in the list
          setChats(prev => prev.map(chat => 
            chat.id === activeChatId 
              ? { ...chat, chat_name: titleResponse.title }
              : chat
          ));
        })
        .catch(error => {
          console.error('Failed to update chat title:', error);
        });
    }

    try {
      await sendChatMessageStream(
        {
          document_id: currentFileState.documentId,
          query,
          provider: selectedModel,
          generate_audio: generateAudio,
        },
        (chunk: StreamChunk) => {
          if (chunk.type === 'text' && typeof chunk.content === 'string') {
            setMessages(prev => {
              const idx = prev.findIndex(m => m.id === assistantMessageId);
              if (idx === -1) return prev;
              const updated = [...prev];
              updated[idx] = {
                ...prev[idx],
                content: prev[idx].content + chunk.content,
              };
              return updated;
            });
          } else if (chunk.type === 'chunks' && Array.isArray(chunk.content)) {
            setMessages(prev => {
              const idx = prev.findIndex(m => m.id === assistantMessageId);
              if (idx === -1) return prev;
              const updated = [...prev];
              updated[idx] = {
                ...prev[idx],
                chunks: chunk.content as string[],
              };
              return updated;
            });
          } else if (chunk.type === 'audio' && typeof chunk.content === 'string') {
            setMessages(prev => {
              const idx = prev.findIndex(m => m.id === assistantMessageId);
              if (idx === -1) return prev;
              const updated = [...prev];
              updated[idx] = {
                ...prev[idx],
                audio_file: chunk.content as string,
              };
              return updated;
            });
          }
        }
      );

      setMessages(prev => {
        const idx = prev.findIndex(m => m.id === assistantMessageId);
        if (idx === -1) return prev;
        const updated = [...prev];
        updated[idx] = {
          ...prev[idx],
          streaming_complete: true,
        };
        return updated;
      });
    } catch (streamError) {
      console.log('Streaming failed, trying non-streaming:', streamError);
      try {
        const response = await sendChatMessage({
          document_id: currentFileState.documentId,
          query,
          provider: selectedModel,
          generate_audio: generateAudio,
        });

        setMessages(prev => {
          const idx = prev.findIndex(m => m.id === assistantMessageId);
          if (idx === -1) return prev;
          const updated = [...prev];
          updated[idx] = {
            ...prev[idx],
            content: response.answer,
            chunks: response.chunks || [],
            audio_file: response.audio_file || undefined,
            streaming_complete: true,
          };
          return updated;
        });
      } catch (apiError) {
        console.error('API Error:', apiError);
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== assistantMessageId);
          return [...filtered, {
            id: assistantMessageId,
            role: 'assistant',
            content: 'Sorry, something went wrong. Please try again.',
            streaming_complete: true,
            timestamp: Date.now() + 1,
          }];
        });
      }
    }

    setIsLoading(false);
  }, [currentFileState.documentId, selectedModel, generateAudio, activeChatId, chats]);

  return (
    <div className="h-screen bg-background text-foreground flex flex-col overflow-hidden">
      {/* Header - Full Width at Top */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-border flex items-center justify-between bg-card">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 rounded-lg hover:bg-secondary transition-colors"
            title={isSidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          >
            {isSidebarOpen ? (
              <PanelLeftClose className="w-5 h-5 text-muted-foreground" />
            ) : (
              <PanelLeft className="w-5 h-5 text-muted-foreground" />
            )}
          </button>
          <div>
            <h1 className="text-xl font-bold text-foreground bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              PDF RAG Assistant
            </h1>
          </div>
        </div>
        <button
          onClick={() => setIsDark(!isDark)}
          className="p-2 rounded-lg hover:bg-secondary transition-colors"
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? (
            <Sun className="w-5 h-5 text-muted-foreground" />
          ) : (
            <Moon className="w-5 h-5 text-muted-foreground" />
          )}
        </button>
      </header>

      {/* Main Content Area - Sidebar + Chat */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        {isSidebarOpen && (
          <ChatSidebar
            chats={chats}
            activeChatId={activeChatId}
            onSelectChat={handleSelectChat}
            onCreateChat={handleCreateChat}
            onDeleteChat={handleDeleteChat}
          />
        )}

        {/* Chat Window */}
        <main className="flex-1 p-6 overflow-hidden">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSendMessage={handleSendMessage}
            disabled={!currentFileState.documentId}
            selectedModel={selectedModel}
            generateAudio={generateAudio}
            onModelChange={setSelectedModel}
            onAudioChange={setGenerateAudio}
            onUploadClick={handleOpenUploadModal}
            fileStatus={currentFileState.status}
          />
        </main>
      </div>

      {/* File Upload Modal */}
      <FileUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        chatId={activeChatId}
        onUploadSuccess={handleUploadSuccess}
        onUploadError={handleUploadError}
      />
    </div>
  );
}

export default App;
