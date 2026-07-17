import React, { useState } from 'react';
import { X, ZoomIn, Info, Sparkles, Loader2 } from 'lucide-react';
import { FigureRef } from '../lib/types';
import { useChatContext } from '../context/ChatContext';

interface FigureViewerProps {
  figure: FigureRef;
}

export function FigureViewer({ figure }: FigureViewerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { submitQuery, sendingMessage } = useChatContext();

  // Re-base the image path if it starts with /api
  const serverBaseUrl = process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL.replace('/api', '')
    : 'http://localhost:8000';
    
  const imageUrl = figure.image_path.startsWith('http')
    ? figure.image_path
    : `${serverBaseUrl}${figure.image_path}`;

  const handleExplain = async () => {
    setIsOpen(false); // Close lightbox
    // Submit the explain figure query
    await submitQuery(`explain figure: ${figure.caption || 'figure'}`);
  };

  return (
    <>
      {/* Inline Preview Figure Card */}
      <div className="flex flex-col rounded-sm border border-neutral-border bg-surface overflow-hidden w-64 shrink-0 transition-all duration-150 hover:border-primary/60">
        {/* Clickable Image Container */}
        <div
          onClick={() => setIsOpen(true)}
          className="relative aspect-video bg-slate-950 overflow-hidden cursor-pointer group"
        >
          <img
            src={imageUrl}
            alt={figure.caption}
            className="w-full h-full object-cover group-hover:scale-[1.01] transition-transform duration-150"
          />
          <div className="absolute inset-0 bg-slate-950/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity duration-150">
            <div className="p-2 rounded-sm bg-slate-950 border border-neutral-border text-primary flex items-center gap-1.5 text-[9px] font-bold font-tech-mono uppercase tracking-widest">
              <ZoomIn className="w-3.5 h-3.5" /> View Figure
            </div>
          </div>
        </div>
        
        {/* Caption Info */}
        <div className="p-3 border-t border-neutral-border flex flex-col gap-1 select-none">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[9px] font-bold text-slate-400 font-tech-mono uppercase tracking-widest flex items-center gap-1">
              <Info className="w-3.5 h-3.5 text-primary shrink-0" /> /figure
            </span>
            <span className="text-[8px] font-tech-mono font-bold text-slate-500 border border-neutral-border/30 bg-background/25 px-1 py-0.5 rounded-sm shrink-0">
              PAGE {figure.page_number}
            </span>
          </div>
          <p className="text-[10px] text-slate-455 font-grotesk-sans font-medium line-clamp-2 leading-relaxed mt-1">
            {figure.caption || 'No caption extracted.'}
          </p>
        </div>
      </div>

      {/* Lightbox Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-slate-950/85 z-50 flex items-center justify-center p-4">
          <button
            onClick={() => setIsOpen(false)}
            className="absolute top-4 right-4 p-2 rounded-sm bg-surface text-slate-455 hover:text-slate-100 hover:bg-background transition-colors border border-neutral-border"
            title="Close Lightbox"
          >
            <X className="w-5 h-5" />
          </button>
          
          <div className="w-full max-w-4xl flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-200 font-sans">
            {/* Center Image */}
            <div className="relative aspect-video rounded-sm bg-slate-950 overflow-hidden border border-neutral-border flex items-center justify-center">
              <img
                src={imageUrl}
                alt={figure.caption}
                className="max-h-[70vh] max-w-full object-contain"
              />
            </div>
            
            {/* Lightbox Caption */}
            <div className="bg-surface border border-neutral-border p-4 rounded-sm max-w-2xl w-full mx-auto flex flex-col gap-3">
              <div className="flex items-center justify-between gap-3">
                <h4 className="font-bold text-[9px] font-tech-mono text-slate-400 uppercase tracking-widest">
                  /figure_reference
                </h4>
                <span className="text-[9px] font-tech-mono font-bold text-primary bg-background/20 px-2 py-0.5 rounded-sm border border-primary/20">
                  PAGE {figure.page_number}
                </span>
              </div>
              <p className="text-xs text-slate-200 font-editorial-serif leading-relaxed italic font-semibold">
                {figure.caption || 'No caption available.'}
              </p>
              
              <button
                onClick={handleExplain}
                disabled={sendingMessage}
                className="mt-1 w-full py-2 px-4 rounded-sm bg-background border border-neutral-border hover:border-primary/50 hover:text-primary disabled:border-neutral-border/30 disabled:text-slate-600 text-slate-355 font-bold font-tech-mono text-xs uppercase tracking-wider transition-colors"
              >
                {sendingMessage ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                    Analyzing figure...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-primary/80" />
                    Explain this figure
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
