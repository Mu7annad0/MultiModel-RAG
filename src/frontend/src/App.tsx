import { useState, useCallback, useEffect } from 'react';
import { FileUpload } from './components/FileUpload';
import { ChatWindow } from './components/ChatWindow';
import { sendChatMessage, sendChatMessageStream, StreamChunk } from './services/api';
import { Message, ModelProvider } from './types';
import { PanelLeftClose, PanelLeftOpen, Sun, Moon } from 'lucide-react';

function App() {
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<ModelProvider>('openai');
  const [generateAudio, setGenerateAudio] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  const handleUploadSuccess = useCallback((docId: string) => {
    setDocumentId(docId);
  }, []);

  const handleSendMessage = useCallback(async (query: string) => {
    if (!documentId) return;

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

    let streamGotContent = false;

    try {
      await sendChatMessageStream(
        {
          document_id: documentId,
          query,
          provider: selectedModel,
          generate_audio: generateAudio,
        },
        (chunk: StreamChunk) => {
          console.log('Stream chunk:', chunk);
          if (chunk.type === 'text' && typeof chunk.content === 'string') {
            streamGotContent = true;
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
            console.log('Audio chunk received:', chunk.content);
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
          document_id: documentId,
          query,
          provider: selectedModel,
          generate_audio: generateAudio,
        });

        console.log('API Response:', response);

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
        const errorMessage: Message = {
          id: assistantMessageId,
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
          streaming_complete: true,
          timestamp: Date.now() + 1,
        };
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== assistantMessageId);
          return [...filtered, errorMessage];
        });
      }
    }

    if (!streamGotContent) {
      console.log('No content from streaming, trying non-streaming...');
      try {
        const response = await sendChatMessage({
          document_id: documentId,
          query,
          provider: selectedModel,
          generate_audio: generateAudio,
        });

        console.log('API Response (fallback):', response);

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
        console.error('API Error (fallback):', apiError);
        if (!streamGotContent) {
          const errorMessage: Message = {
            id: assistantMessageId,
            role: 'assistant',
            content: 'Sorry, something went wrong. Please try again.',
            streaming_complete: true,
            timestamp: Date.now() + 1,
          };
          setMessages(prev => {
            const filtered = prev.filter(m => m.id !== assistantMessageId);
            return [...filtered, errorMessage];
          });
        }
      }
    }

    setIsLoading(false);
  }, [documentId, selectedModel, generateAudio]);

  return (
    <div className="h-screen bg-background text-foreground flex flex-col overflow-hidden">
      <header className="flex-shrink-0 px-6 py-4 border-b border-border flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            PDF RAG Assistant
          </h1>
          <p className="text-muted-foreground mt-0.5 text-xs">
            Upload a PDF and chat with AI about its contents
          </p>
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

      <div className="flex-1 flex gap-6 p-6 overflow-hidden">
        {isSidebarOpen && (
          <aside className="w-72 flex-shrink-0 transition-all duration-300">
            <div className="bg-card rounded-2xl border border-border p-5 shadow-sm h-full flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Upload Document</h2>
                <button
                  onClick={() => setIsSidebarOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-secondary transition-colors"
                  title="Close sidebar"
                >
                  <PanelLeftClose className="w-4 h-4 text-muted-foreground" />
                </button>
              </div>
              <FileUpload
                onUploadSuccess={handleUploadSuccess}
                disabled={false}
                documentId={documentId}
              />
            </div>
          </aside>
        )}
        {!isSidebarOpen && (
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="flex-shrink-0 self-start p-2.5 rounded-xl bg-card border border-border hover:border-primary/50 transition-all shadow-sm"
            title="Open sidebar"
          >
            <PanelLeftOpen className="w-5 h-5 text-muted-foreground" />
          </button>
        )}

        <main className="flex-1 overflow-hidden">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSendMessage={handleSendMessage}
            disabled={!documentId}
            selectedModel={selectedModel}
            generateAudio={generateAudio}
            onModelChange={setSelectedModel}
            onAudioChange={setGenerateAudio}
          />
        </main>
      </div>
    </div>
  );
}

export default App;
