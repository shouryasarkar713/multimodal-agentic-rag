import React, { useState } from 'react';
import Link from 'next/link';
import { MessageSquare, Bot, User, Share2, FileText, Activity } from 'lucide-react';
import { Message, Citation } from '../lib/types';
import { ConfidenceBadge } from './ConfidenceBadge';
import { ExportButton } from './ExportButton';
import { CitationCard } from './CitationCard';
import { FigureViewer } from './FigureViewer';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const hasCitations = message.citations && message.citations.length > 0;
  const hasFigures = message.figure_refs && message.figure_refs.length > 0;

  // Render text content and highlight citations/figures
  const renderMessageBody = (text: string) => {
    // Regex matching [N] or [citation not found]
    const regex = /(\[(\d+)\]|\[citation not found\]|\[Figure from source (\d+)\])/g;
    const parts = text.split(regex);
    if (parts.length === 1) {
      return <p className="whitespace-pre-wrap leading-relaxed">{text}</p>;
    }

    return (
      <p className="whitespace-pre-wrap leading-relaxed">
        {parts.map((part, idx) => {
          if (part === undefined) return null;
          if (/^\d+$/.test(part)) return null;
          
          // If it matches [N]
          if (part.startsWith('[') && part.endsWith(']')) {
            if (part === '[citation not found]') {
              return (
                <span
                  key={idx}
                  className="inline-block px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-[9px] font-mono font-bold select-none"
                >
                  citation not found
                </span>
              );
            }
            if (part.startsWith('[Figure from source')) {
              const numStr = part.match(/\d+/)?.[0];
              const idxNum = numStr ? parseInt(numStr, 10) : null;
              return (
                <span
                  key={idx}
                  className="inline-block px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[9px] font-mono font-bold select-none cursor-default"
                >
                  {part}
                </span>
              );
            }
            // Standard citation [N]
            const num = parseInt(part.slice(1, -1), 10);
            const matchedCitation = message.citations?.[num - 1];
            
            if (matchedCitation) {
              return (
                <span
                  key={idx}
                  onClick={() => {
                    // Trigger click event or show a notification
                    const el = document.getElementById(`citation-card-${num - 1}`);
                    if (el) {
                      el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                      // Add temporary highlight animation
                      el.classList.add('ring-2', 'ring-indigo-500');
                      setTimeout(() => el.classList.remove('ring-2', 'ring-indigo-500'), 1500);
                    }
                  }}
                  className="inline-block px-1.5 py-0.5 rounded bg-indigo-600/15 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-600 hover:text-white transition-colors text-[9px] font-mono font-bold select-none cursor-pointer"
                  title={`Source: ${matchedCitation.document_title}, Page ${matchedCitation.page_number}`}
                >
                  {part}
                </span>
              );
            }
            return (
              <span
                key={idx}
                className="inline-block px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[9px] font-mono font-bold select-none"
              >
                {part}
              </span>
            );
          }
          return part;
        })}
      </p>
    );
  };

  return (
    <div className={`flex w-full gap-4 py-6 px-4 md:px-6 border-b transition-colors duration-150 ${
      isUser 
        ? 'bg-slate-950/20 border-slate-900/40 justify-end' 
        : 'bg-indigo-950/5 border-indigo-950/10 justify-start'
    }`}>
      <div className={`flex gap-4 max-w-4xl w-full ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Role Icon Avatar */}
        <div className={`w-8 h-8 rounded-xl border flex items-center justify-center shrink-0 shadow-sm ${
          isUser 
            ? 'bg-slate-800 border-slate-750 text-slate-300' 
            : 'bg-indigo-600 border-indigo-500 text-white'
        }`}>
          {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
        </div>

        {/* Message Content Container */}
        <div className="flex flex-col gap-3 flex-1 min-w-0">
          {/* Header Metadata */}
          {!isUser && (
            <div className="flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-xs text-indigo-400 uppercase tracking-wider">
                  Copilot Response
                </span>
                {message.confidence !== undefined && message.confidence !== null && (
                  <ConfidenceBadge score={message.confidence} />
                )}
              </div>
              
              {/* Top Right Trace Trigger */}
              {message.trace_id && (
                <Link
                  href={`/trace/${message.trace_id}`}
                  className="inline-flex items-center gap-1 text-[10px] font-extrabold text-slate-500 hover:text-indigo-400 transition-colors"
                >
                  <Activity className="w-3.5 h-3.5" /> View Trace Timeline
                </Link>
              )}
            </div>
          )}

          {isUser && (
            <span className="font-extrabold text-xs text-slate-500 uppercase tracking-wider">
              You
            </span>
          )}

          {/* Text Body */}
          <div className={`text-slate-200 text-xs md:text-sm font-semibold leading-relaxed ${isUser ? 'bg-slate-800/40 border border-slate-800/80 p-4 rounded-2xl max-w-xl self-end' : ''}`}>
            {renderMessageBody(message.content)}
          </div>

          {/* Side-Scrollable Citations List */}
          {!isUser && hasCitations && (
            <div className="flex flex-col gap-2.5 mt-3 border-t border-slate-800/20 pt-4">
              <span className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">
                Source Citations
              </span>
              <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-800">
                {message.citations?.map((cit, idx) => (
                  <div id={`citation-card-${idx}`} key={cit.chunk_id}>
                    <CitationCard citation={cit} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Side-Scrollable Figures List */}
          {!isUser && hasFigures && (
            <div className="flex flex-col gap-2.5 mt-3 border-t border-slate-800/20 pt-4">
              <span className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">
                Referenced Figures
              </span>
              <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-800">
                {message.figure_refs?.map((fig) => (
                  <FigureViewer key={fig.chunk_id} figure={fig} />
                ))}
              </div>
            </div>
          )}

          {/* Footer Actions Row */}
          {!isUser && (
            <div className="flex items-center justify-between mt-4 border-t border-slate-850 pt-3">
              <div className="flex items-center gap-2">
                <ExportButton messageId={message.id} />
              </div>
              <span className="text-[9px] font-mono text-slate-600 font-semibold select-none">
                {message.created_at ? new Date(message.created_at).toLocaleTimeString() : ''}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
