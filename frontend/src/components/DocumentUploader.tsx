import React, { useState, useCallback } from 'react';
import { UploadCloud, FileText, Loader2, AlertCircle } from 'lucide-react';

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
    <div className="w-full flex flex-col gap-3 font-sans">
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        className={`relative w-full py-10 px-6 rounded-sm border border-dashed flex flex-col items-center justify-center gap-4 transition-all duration-150 ${
          dragActive
            ? 'border-primary bg-background/50 scale-[1.0]'
            : 'border-neutral-border bg-background/10 hover:border-slate-500 hover:bg-background/20'
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
          {/* Simple typography/icon treatment without border container boxes */}
          <div className="mb-2 text-slate-400 hover:text-primary transition-colors">
            {uploading ? (
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            ) : (
              <UploadCloud className="w-6 h-6" />
            )}
          </div>
          
          <p className="text-xs font-bold uppercase tracking-wider text-slate-200 font-tech-mono">
            {uploading ? '/indexing new paper...' : 'Drop PDF to Index'}
          </p>
          <p className="text-[10px] text-slate-500 mt-1 font-semibold font-tech-mono">
            PDF format only, up to 50 MB
          </p>
        </label>
        
        {uploading && (
          <div className="absolute bottom-3 left-4 right-4">
            <div className="h-1.5 w-full bg-slate-950 border border-neutral-border rounded-sm overflow-hidden">
              <div className="h-full bg-primary rounded-sm animate-progress" />
            </div>
            <p className="text-[9px] text-center text-primary/80 font-tech-mono mt-1 font-bold animate-pulse uppercase tracking-wider">
              Stepped parsing, chunking, and embedding active
            </p>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-2.5 p-3 rounded-sm border border-red-500/20 bg-red-500/5 text-red-400 text-xs font-semibold font-tech-mono">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="flex-1 uppercase tracking-wide text-[10px]">{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-[9px] uppercase font-bold hover:text-red-300 px-1.5 py-0.5 rounded-sm border border-red-500/20 hover:bg-red-500/10 transition-colors"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
}
