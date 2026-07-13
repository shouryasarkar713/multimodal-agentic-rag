import React, { useState } from 'react';
import { Eye, X, ZoomIn, Info } from 'lucide-react';
import { FigureRef } from '../lib/types';

interface FigureViewerProps {
  figure: FigureRef;
}

export function FigureViewer({ figure }: FigureViewerProps) {
  const [isOpen, setIsOpen] = useState(false);

  const serverBaseUrl = process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL.replace('/api', '')
    : 'http://localhost:8000';
    
  const imageUrl = figure.image_path.startsWith('http')
    ? figure.image_path
    : `${serverBaseUrl}${figure.image_path}`;

  return (
    <>
      <div className="flex flex-col rounded-xl border border-slate-800 bg-slate-950 overflow-hidden w-64 shrink-0 transition-all duration-200 hover:border-indigo-500/50 hover:shadow-lg">
        <div
          onClick={() => setIsOpen(true)}
          className="relative aspect-video bg-slate-900 overflow-hidden cursor-pointer group"
        >
          <img
            src={imageUrl}
            alt={figure.caption}
            className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-300"
          />
          <div className="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity duration-200">
            <div className="p-2 rounded-full bg-slate-900/90 text-indigo-400 border border-slate-700/50 flex items-center gap-1.5 text-[10px] font-bold shadow-lg">
              <ZoomIn className="w-3.5 h-3.5" /> View Figure
            </div>
          </div>
        </div>
        
        <div className="p-3 border-t border-slate-900 flex flex-col gap-1 select-none">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] font-extrabold text-slate-300 flex items-center gap-1">
              <Info className="w-3 h-3 text-indigo-400" /> Extracted Figure
            </span>
            <span className="text-[9px] font-mono font-bold text-slate-500 bg-slate-900 px-1 py-0.5 rounded">
              Page {figure.page_number}
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-medium line-clamp-2 leading-relaxed mt-1">
            {figure.caption || 'No caption extracted.'}
          </p>
        </div>
      </div>

      {isOpen && (
        <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <button
            onClick={() => setIsOpen(false)}
            className="absolute top-4 right-4 p-2 rounded-xl bg-slate-900 text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors border border-slate-800"
            title="Close Lightbox"
          >
            <X className="w-5 h-5" />
          </button>
          
          <div className="w-full max-w-4xl flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="relative aspect-video rounded-2xl bg-slate-900 overflow-hidden border border-slate-800 flex items-center justify-center">
              <img
                src={imageUrl}
                alt={figure.caption}
                className="max-h-[70vh] max-w-full object-contain"
              />
            </div>
            
            <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl max-w-2xl mx-auto">
              <div className="flex items-center justify-between gap-3 mb-1.5">
                <h4 className="font-extrabold text-xs text-slate-200">
                  FIGURE REFERENCE
                </h4>
                <span className="text-[10px] font-mono font-bold text-indigo-400 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-900/50">
                  Page {figure.page_number}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-semibold leading-relaxed">
                {figure.caption || 'No caption available.'}
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
