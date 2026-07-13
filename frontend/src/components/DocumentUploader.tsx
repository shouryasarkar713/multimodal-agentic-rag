import React, { useState, useCallback } from 'react';
import { UploadCloud, Loader2, AlertCircle } from 'lucide-react';

interface DocumentUploaderProps {
  onUpload: (file: File) => Promise<void>;
  uploading: boolean;
  error: string | null;
  setError: (err: string | null) => void;
}

export function DocumentUploader({
  onUpload,
  uploading,
  error,
  setError,
}: DocumentUploaderProps) {
  const [dragActive, setDragActive] = useState<boolean>(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files[0]);
    }
  }, [onUpload]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  }, [onUpload]);

  return (
    <div className="w-full flex flex-col gap-3">
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        className={`relative w-full py-12 px-6 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center gap-4 transition-all duration-300 ${
          dragActive
            ? 'border-indigo-500 bg-indigo-500/5 shadow-[0_0_20px_rgba(99,102,241,0.15)] scale-[1.01]'
            : 'border-slate-800 bg-slate-800/20 hover:border-slate-700/60 hover:bg-slate-800/40 hover:shadow-[0_0_15px_rgba(99,102,241,0.05)]'
        }`}
      >
        <input
          type="file"
          id="file-upload-input"
          className="hidden"
          accept=".pdf"
          onChange={handleChange}
          disabled={uploading}
        />
        
        <label
          htmlFor="file-upload-input"
          className="flex flex-col items-center justify-center cursor-pointer select-none text-center"
        >
          <div className={`p-4 rounded-full bg-slate-800 border mb-3 transition-colors ${dragActive ? 'border-indigo-500 text-indigo-400' : 'border-slate-700 text-slate-400'}`}>
            {uploading ? (
              <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
            ) : (
              <UploadCloud className="w-8 h-8" />
            )}
          </div>
          
          <p className="text-sm font-semibold text-slate-200">
            {uploading ? 'Processing document chunks...' : 'Drag and drop your research paper here'}
          </p>
          <p className="text-xs text-slate-500 mt-1.5 font-medium">
            PDF format only, up to 50 MB
          </p>
        </label>
        
        {uploading && (
          <div className="absolute bottom-4 left-6 right-6">
            <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 rounded-full animate-progress" />
            </div>
            <p className="text-[10px] text-center text-indigo-400/80 font-mono mt-1.5 font-medium animate-pulse">
              10-step parsing, chunking, and embedding pipeline active
            </p>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2.5 p-3 rounded-lg border border-red-500/20 bg-red-500/5 text-red-400 text-xs font-semibold">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-[10px] uppercase font-bold hover:text-red-300 px-1.5 py-0.5 rounded hover:bg-red-500/10 transition-colors"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
}
