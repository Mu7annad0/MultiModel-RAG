import React, { useState, useCallback, useRef } from 'react';
import { X, FileText, Upload, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { uploadFile } from '../services/api';
import { FileUploadState } from '../types';

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  chatId: number | null;
  onUploadSuccess: (documentId: string, chatId: number, filename: string) => void;
  onUploadError: (error: string) => void;
}

export const FileUploadModal: React.FC<FileUploadModalProps> = ({
  isOpen,
  onClose,
  chatId,
  onUploadSuccess,
  onUploadError,
}) => {
  const [state, setState] = useState<FileUploadState>({
    file: null,
    isUploading: false,
    progress: 0,
    error: null,
    documentId: null,
    savedFileSize: null,
    status: 'idle',
  });
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback(async (file: File) => {
    if (!file.type.includes('pdf')) {
      const isImage = file.type.startsWith('image/');
      setState(prev => ({
        ...prev,
        error: isImage
          ? 'Image files are not supported. Please upload a PDF document.'
          : 'Only PDF files are allowed. Please upload a valid PDF.',
        status: 'error',
      }));
      return;
    }

    setState({
      file,
      isUploading: true,
      progress: 0,
      error: null,
      documentId: null,
      savedFileSize: null,
      status: 'uploading',
    });

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90),
        }));
      }, 200);

      const response = await uploadFile(file, chatId || undefined);

      clearInterval(progressInterval);

      setState({
        file,
        isUploading: false,
        progress: 100,
        error: null,
        documentId: response.document_id,
        savedFileSize: null,
        status: 'ready',
      });

      onUploadSuccess(response.document_id, response.chat_id, file.name);
      
      // Close modal after a brief delay
      setTimeout(() => {
        onClose();
        // Reset state after closing
        setState({
          file: null,
          isUploading: false,
          progress: 0,
          error: null,
          documentId: null,
          savedFileSize: null,
          status: 'idle',
        });
      }, 1500);
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } }; message?: string };
      const errorMessage = axiosError.response?.data?.error || axiosError.message || 'Upload failed';

      let formattedError = errorMessage;
      if (errorMessage.includes('100 pages')) {
        formattedError = 'File exceeds maximum of 100 pages';
      } else if (errorMessage.includes('Unsupported file format')) {
        formattedError = 'Only PDF files are supported';
      }

      setState(prev => ({
        ...prev,
        isUploading: false,
        progress: 0,
        error: formattedError,
        status: 'error',
      }));

      onUploadError(formattedError);
    }
  }, [chatId, onUploadSuccess, onUploadError, onClose]);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    if (state.isUploading) return;

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [state.isUploading, handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const handleClose = useCallback(() => {
    if (!state.isUploading) {
      onClose();
      setState({
        file: null,
        isUploading: false,
        progress: 0,
        error: null,
        documentId: null,
        savedFileSize: null,
        status: 'idle',
      });
    }
  }, [onClose, state.isUploading]);

  if (!isOpen) return null;

  const getStatusDisplay = () => {
    switch (state.status) {
      case 'uploading':
        return (
          <div className="flex items-center gap-2 text-blue-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Uploading...</span>
          </div>
        );
      case 'indexing':
        return (
          <div className="flex items-center gap-2 text-yellow-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Indexing...</span>
          </div>
        );
      case 'ready':
        return (
          <div className="flex items-center gap-2 text-green-500">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm">Ready</span>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center gap-2 text-red-500">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">Failed</span>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-card rounded-2xl border border-border shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-foreground">Upload PDF</h2>
          <button
            onClick={handleClose}
            disabled={state.isUploading}
            className="p-2 rounded-lg hover:bg-secondary transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => !state.isUploading && fileInputRef.current?.click()}
          className={`
            relative border-2 border-dashed rounded-xl p-8 transition-all duration-300 cursor-pointer
            ${isDragging
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/50 hover:bg-card/50'
            }
            ${state.isUploading ? 'opacity-50 cursor-not-allowed' : ''}
            ${state.error ? 'border-red-500' : ''}
            ${state.status === 'ready' ? 'border-green-500 bg-green-500/5' : ''}
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleInputChange}
            className="hidden"
            disabled={state.isUploading}
          />

          {state.isUploading ? (
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 rounded-full border-4 border-primary border-t-transparent animate-spin" />
              <p className="text-sm text-muted-foreground">Uploading...</p>
              <div className="w-full max-w-xs h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${state.progress}%` }}
                />
              </div>
            </div>
          ) : state.file ? (
            <div className="flex flex-col items-center gap-4">
              <div className="p-4 rounded-full bg-primary/10">
                <FileText className="w-8 h-8 text-primary" />
              </div>
              <div className="text-center">
                <p className="font-medium text-foreground truncate max-w-[200px]">
                  {state.file.name}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {(state.file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="p-4 rounded-full bg-secondary">
                <Upload className="w-8 h-8 text-muted-foreground" />
              </div>
              <div className="text-center">
                <p className="font-medium text-foreground">Drop your PDF here</p>
                <p className="text-sm text-muted-foreground mt-1">
                  or click to browse (max 100 pages)
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Status Display */}
        <div className="mt-4 flex justify-center">
          {getStatusDisplay()}
        </div>

        {/* Error Display */}
        {state.error && (
          <div className="mt-4 flex items-center justify-center gap-2 p-3 rounded-lg bg-red-500/10 text-red-500">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <p className="text-sm">{state.error}</p>
          </div>
        )}
      </div>
    </div>
  );
};
