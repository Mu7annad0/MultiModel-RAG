import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Upload, FileText, X, CheckCircle, AlertCircle } from 'lucide-react';
import { uploadFile } from '../services/api';
import { FileUploadState } from '../types';

interface FileUploadProps {
  onUploadSuccess: (documentId: string) => void;
  disabled?: boolean;
  documentId?: string | null;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess, disabled, documentId }) => {
  const [state, setState] = useState<FileUploadState>({
    file: null,
    isUploading: false,
    progress: 0,
    error: null,
    documentId: null,
    savedFileSize: null,
  });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (documentId) {
      const savedFileName = localStorage.getItem(`file_${documentId}`);
      const savedFileSize = localStorage.getItem(`file_size_${documentId}`);
      if (savedFileName) {
        setState(prev => ({
          ...prev,
          documentId,
          file: new File([], savedFileName),
          savedFileSize: savedFileSize ? parseInt(savedFileSize) : null,
        }));
      } else {
        setState(prev => ({
          ...prev,
          documentId,
        }));
      }
    }
  }, [documentId]);

  const handleFileSelect = useCallback(async (file: File) => {
    if (!file.type.includes('pdf')) {
      const isImage = file.type.startsWith('image/');
      setState(prev => ({
        ...prev,
        error: isImage 
          ? 'Image files are not supported. Please upload a PDF document.'
          : 'Only PDF files are allowed. Please upload a valid PDF.',
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
    });

    try {
      const response = await uploadFile(file);
      setState({
        file,
        isUploading: false,
        progress: 100,
        error: null,
        documentId: response.document_id,
        savedFileSize: null,
      });
      localStorage.setItem(`file_${response.document_id}`, file.name);
      localStorage.setItem(`file_size_${response.document_id}`, file.size.toString());
      onUploadSuccess(response.document_id);
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: string } }, message?: string };
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
        savedFileSize: null,
      }));
    }
  }, [onUploadSuccess]);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    if (disabled || state.isUploading) return;

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [disabled, state.isUploading, handleFileSelect]);

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

  const handleClear = useCallback(() => {
    if (state.documentId) {
      localStorage.removeItem(`file_${state.documentId}`);
      localStorage.removeItem(`file_size_${state.documentId}`);
    }
    setState({
      file: null,
      isUploading: false,
      progress: 0,
      error: null,
      documentId: null,
      savedFileSize: null,
    });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [state.documentId]);

  return (
    <div className="w-full space-y-3">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          relative border-2 border-dashed rounded-xl p-6 transition-all duration-300
          ${isDragging 
            ? 'border-primary bg-primary/5' 
            : 'border-border hover:border-primary/50 hover:bg-card/50'
          }
          ${disabled || state.isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          ${state.error ? 'border-destructive' : ''}
        `}
        onClick={() => !disabled && !state.isUploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleInputChange}
          className="hidden"
          disabled={disabled || state.isUploading}
        />

        {state.isUploading ? (
          <div className="flex flex-col items-center gap-3">
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
          <div className="flex items-center justify-between w-full gap-3">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className="p-3 rounded-full bg-primary/10 flex-shrink-0">
                <FileText className="w-6 h-6 text-primary" />
              </div>
              <div className="text-left flex-1 min-w-0">
                <p className="font-medium text-foreground truncate">
                  {state.file.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {state.savedFileSize 
                    ? `${(state.savedFileSize / 1024 / 1024).toFixed(2)} MB`
                    : `${(state.file.size / 1024 / 1024).toFixed(2)} MB`
                  }
                </p>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleClear();
              }}
              className="p-2 rounded-full hover:bg-secondary transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="p-3 rounded-full bg-secondary">
              <Upload className="w-6 h-6 text-muted-foreground" />
            </div>
            <div className="text-center">
              <p className="font-medium text-foreground">
                Drop your PDF here
              </p>
              <p className="text-sm text-muted-foreground">
                or click to browse (max 100 pages)
              </p>
            </div>
          </div>
        )}
      </div>

      {state.documentId && (
        <div className="flex items-center justify-center gap-2 text-emerald-600">
          <CheckCircle className="w-4 h-4" />
          <span className="text-sm">Document indexed</span>
        </div>
      )}

      {state.error && (
        <div className="flex items-center justify-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive animate-fade-in">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <p className="text-sm">{state.error}</p>
        </div>
      )}
    </div>
  );
};
