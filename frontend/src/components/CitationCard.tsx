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
      {/* Small Inline Card */}
      <div
        onClick={() => setIsOpen(true)}
        className="flex flex-col p-3 rounded-sm border border-neutral-border bg-surface hover:bg-background/40 hover:border-slate-500 cursor-pointer w-64 shrink-0 select-none transition-all duration-150"
      >
        <div className="flex items-start justify-between gap-2 mb-1.5 font-sans">
          <div className="flex items-center gap-1.5 min-w-0">
            <FileText className="w-3.5 h-3.5 text-primary shrink-0" />
            <span className="text-[11px] font-bold text-slate-200 truncate font-editorial-serif">
              {citation.document_title}
            </span>
          </div>
          <span className="text-[8px] font-tech-mono font-bold text-slate-500 border border-neutral-border/30 bg-background/25 px-1 py-0.5 rounded-sm shrink-0">
            PAGE {citation.page_number}
          </span>
        </div>
        
        {citation.section_title && (
          <div className="text-[9px] text-primary/80 font-bold font-tech-mono uppercase tracking-wider truncate mb-2">
            SEC: {citation.section_title}
          </div>
        )}
        
        <p className="text-[10px] text-slate-400 font-grotesk-sans font-medium line-clamp-3 leading-relaxed">
          {citation.excerpt}
        </p>
      </div>

      {/* Modal Dialog */}
      {isOpen && (
        <div className="fixed inset-0 bg-slate-950/80 z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-sm border border-neutral-border bg-surface p-6 relative flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-200 font-sans">
            {/* Modal Header */}
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                <div>
                  <h3 className="font-bold text-md text-slate-100 font-editorial-serif pr-6">
                    {citation.document_title}
                  </h3>
                  <div className="flex items-center gap-2 text-[10px] text-slate-500 font-bold font-tech-mono mt-1 uppercase tracking-wider">
                    <span>Page {citation.page_number}</span>
                    {citation.section_title && (
                      <>
                        <span>•</span>
                        <span className="text-primary/85">Section: {citation.section_title}</span>
                      </>
                    )}
                    <span>•</span>
                    <span className="text-slate-400">Score: {citation.relevance_score?.toFixed(1) || '5.0'}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="absolute top-4 right-4 p-1 rounded-sm text-slate-500 hover:bg-background hover:text-slate-200 transition-colors border border-transparent hover:border-neutral-border/30"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content Excerpt */}
            <div className="bg-slate-950/50 p-4 rounded-sm border border-neutral-border/60">
              <div className="text-[9px] uppercase font-bold text-primary font-tech-mono tracking-widest mb-2">
                /extracted_excerpt
              </div>
              <p className="text-xs text-slate-300 font-grotesk-sans font-semibold leading-relaxed whitespace-pre-wrap">
                {citation.excerpt}
              </p>
            </div>

            {/* Modal Actions */}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsOpen(false)}
                className="px-4 py-1.5 rounded-sm bg-background border border-neutral-border text-xs font-bold font-tech-mono uppercase tracking-wider text-slate-350 hover:text-primary hover:border-primary/50 transition-colors"
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
