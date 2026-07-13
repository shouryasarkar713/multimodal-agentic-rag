import React, { useState } from 'react';
import { FileText, X } from 'lucide-react';
import { Citation } from '../lib/types';

interface CitationCardProps {
  citation: Citation;
}

export function CitationCard({ citation }: CitationCardProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <div
        onClick={() => setIsOpen(true)}
        className="flex flex-col p-3 rounded-xl border border-slate-800 bg-slate-900/40 hover:bg-slate-800/60 hover:border-slate-700/60 cursor-pointer w-64 shrink-0 select-none transition-all duration-200"
      >
        <div className="flex items-start justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-1.5 min-w-0">
            <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span className="text-[10px] font-bold text-slate-300 truncate">
              {citation.document_title}
            </span>
          </div>
          <span className="text-[9px] font-mono font-bold text-slate-500 bg-slate-800 px-1 py-0.5 rounded shrink-0">
            Page {citation.page_number}
          </span>
        </div>
        
        {citation.section_title && (
          <div className="text-[9px] text-indigo-400/80 font-bold truncate mb-2">
            Section: {citation.section_title}
          </div>
        )}
        
        <p className="text-[10px] text-slate-400 font-medium line-clamp-3 leading-relaxed">
          {citation.excerpt}
        </p>
      </div>

      {isOpen && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl p-6 relative flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-indigo-400" />
                <div>
                  <h3 className="font-extrabold text-sm text-slate-100 pr-6">
                    {citation.document_title}
                  </h3>
                  <div className="flex items-center gap-2 text-[10px] text-slate-500 font-bold mt-0.5">
                    <span>Page {citation.page_number}</span>
                    {citation.section_title && (
                      <>
                        <span>•</span>
                        <span className="text-indigo-400/80">Section: {citation.section_title}</span>
                      </>
                    )}
                    <span>•</span>
                    <span className="text-slate-500 font-mono">Score: {citation.relevance_score?.toFixed(1) || '5.0'}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-500 hover:bg-slate-800 hover:text-slate-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
              <div className="text-[10px] uppercase font-bold text-indigo-400 tracking-wider mb-2">
                Extracted Excerpt
              </div>
              <p className="text-xs text-slate-300 font-semibold leading-relaxed whitespace-pre-wrap">
                {citation.excerpt}
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-xs font-bold text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
