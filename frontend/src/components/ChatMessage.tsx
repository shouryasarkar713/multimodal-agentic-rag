import React, { useState } from 'react';
import Link from 'next/link';
import { MessageSquare, Bot, User, Share2, FileText, Activity } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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

  const processTextWithCitations = (text: string) => {
    const regex = /(\[(\d+)\]|\[citation not found\]|\[Figure from source (\d+)\])/g;
    const parts = text.split(regex);
    if (parts.length === 1) {
      return text;
    }

    return parts.map((part, idx) => {
      if (part === undefined) return null;
      if (/^\d+$/.test(part)) return null;
      
      // If it matches [N]
      if (part.startsWith('[') && part.endsWith(']')) {
        if (part === '[citation not found]') {
          return (
            <span
              key={idx}
              className="inline-block px-1.5 py-0.5 mx-0.5 rounded-sm bg-red-500/10 text-red-400 border border-red-500/20 text-[8px] font-tech-mono font-bold select-none uppercase tracking-wide animate-pulse"
            >
              citation not found
            </span>
          );
        }
        if (part.startsWith('[Figure from source')) {
          return (
            <span
              key={idx}
              className="inline-block px-1.5 py-0.5 mx-0.5 rounded-sm bg-primary/10 text-primary border border-primary/20 text-[8px] font-tech-mono font-bold select-none cursor-default uppercase tracking-wide"
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
                const el = document.getElementById(`citation-card-${num - 1}`);
                if (el) {
                  el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                  el.classList.add('ring-1', 'ring-primary');
                  setTimeout(() => el.classList.remove('ring-1', 'ring-primary'), 1500);
                }
              }}
              className="inline-block px-1.5 py-0.5 mx-0.5 rounded-sm bg-primary/10 text-primary border border-primary/20 hover:bg-primary hover:text-slate-950 transition-colors text-[8px] font-tech-mono font-bold select-none cursor-pointer tracking-wider"
              title={`Source: ${matchedCitation.document_title}, Page ${matchedCitation.page_number}`}
            >
              {part}
            </span>
          );
        }
        return (
          <span
            key={idx}
            className="inline-block px-1.5 py-0.5 mx-0.5 rounded-sm bg-slate-800 text-slate-400 text-[8px] font-tech-mono font-bold select-none tracking-wider"
          >
            {part}
          </span>
        );
      }
      return part;
    });
  };

  const renderWithCitations = (node: React.ReactNode): React.ReactNode => {
    if (typeof node === 'string') {
      return processTextWithCitations(node);
    }
    if (React.isValidElement(node)) {
      if (node.props.children) {
        return React.cloneElement(
          node,
          // @ts-ignore
          node.props,
          React.Children.map(node.props.children, child => renderWithCitations(child))
        );
      }
    }
    return node;
  };

  const components = {
    p: ({ children }: any) => <p className="leading-relaxed font-editorial-serif text-slate-200 text-sm md:text-base font-medium mb-4">{React.Children.map(children, child => renderWithCitations(child))}</p>,
    li: ({ children }: any) => <li className="leading-relaxed font-sans text-slate-350 text-xs md:text-sm mb-1.5 list-disc ml-5">{React.Children.map(children, child => renderWithCitations(child))}</li>,
    td: ({ children }: any) => <td className="border border-neutral-border/40 p-2.5 text-xs font-sans text-slate-250">{React.Children.map(children, child => renderWithCitations(child))}</td>,
    th: ({ children }: any) => <th className="border border-neutral-border/45 bg-slate-900/50 p-2.5 text-xs font-tech-mono font-bold text-slate-350 uppercase tracking-wider">{React.Children.map(children, child => renderWithCitations(child))}</th>,
    h1: ({ children }: any) => <h1 className="font-editorial-serif text-xl md:text-2xl font-bold text-slate-100 mt-6 mb-3 border-b border-neutral-border/20 pb-1">{children}</h1>,
    h2: ({ children }: any) => <h2 className="font-editorial-serif text-lg md:text-xl font-bold text-slate-100 mt-5 mb-2.5">{children}</h2>,
    h3: ({ children }: any) => <h3 className="font-editorial-serif text-base md:text-lg font-bold text-slate-200 mt-4 mb-2">{children}</h3>,
    h4: ({ children }: any) => <h4 className="font-editorial-serif text-sm md:text-base font-bold text-slate-200 mt-3 mb-1.5">{children}</h4>,
    table: ({ children }: any) => (
      <div className="overflow-x-auto my-5 border border-neutral-border/40 rounded-sm">
        <table className="min-w-full border-collapse text-left">{children}</table>
      </div>
    ),
    pre: ({ children }: any) => <pre className="bg-slate-950/80 border border-neutral-border/40 p-4 rounded-sm my-4 overflow-x-auto font-tech-mono text-xs text-slate-300">{children}</pre>,
    code: ({ children }: any) => <code className="bg-slate-900/50 border border-neutral-border/20 px-1 py-0.5 rounded-sm font-tech-mono text-xs text-primary">{children}</code>
  };

  // Render text content and highlight citations/figures
  const renderMessageBody = (text: string) => {
    if (isUser) {
      return <p className="whitespace-pre-wrap leading-relaxed font-editorial-serif text-slate-200 text-sm md:text-base font-medium">{text}</p>;
    }

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {text}
      </ReactMarkdown>
    );
  };

  return (
    <div className={`flex w-full gap-4 py-6 px-4 md:px-6 border-b border-neutral-border/40 transition-colors duration-150 ${
      isUser 
        ? 'bg-background/10 border-neutral-border/20 justify-end' 
        : 'bg-surface/20 border-neutral-border/20 justify-start'
    }`}>
      <div className={`flex gap-4 max-w-4xl w-full ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Role Icon Avatar */}
        <div className={`w-8 h-8 rounded-sm border flex items-center justify-center shrink-0 shadow-sm ${
          isUser 
            ? 'bg-slate-950 border-neutral-border text-slate-500' 
            : 'bg-background border-primary/30 text-primary'
        }`}>
          {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
        </div>

        {/* Message Content Container */}
        <div className="flex flex-col gap-3 flex-1 min-w-0 font-sans">
          {/* Header Metadata */}
          {!isUser && (
            <div className="flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex items-center gap-2">
                <span className="font-bold text-[10px] text-primary font-tech-mono uppercase tracking-widest">
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
                  className="inline-flex items-center gap-1 text-[9px] font-bold font-tech-mono text-slate-500 hover:text-primary transition-colors uppercase tracking-wider border border-neutral-border/25 bg-background/20 px-2 py-0.5 rounded-sm"
                >
                  <Activity className="w-3.5 h-3.5 text-primary/80" /> Trace node
                </Link>
              )}
            </div>
          )}

          {isUser && (
            <span className="font-bold text-[10px] text-slate-500 font-tech-mono uppercase tracking-widest">
              Index query trigger
            </span>
          )}

          {/* Text Body */}
          <div className={`text-slate-200 leading-relaxed ${isUser ? 'border-l-2 border-primary/70 pl-4 py-1 max-w-2xl self-end italic font-grotesk-sans font-medium text-xs md:text-sm' : ''}`}>
            {renderMessageBody(message.content)}
          </div>

          {/* Side-Scrollable Citations List */}
          {!isUser && hasCitations && (
            <div className="flex flex-col gap-2 mt-3 border-t border-neutral-border/20 pt-4">
              <span className="text-[10px] font-bold text-slate-500 font-tech-mono uppercase tracking-widest pl-1">
                Source Citations
              </span>
              <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-800">
                {message.citations?.map((cit, idx) => (
                  <div id={`citation-card-${idx}`} key={cit.chunk_id} className="transition-all duration-300">
                    <CitationCard citation={cit} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Side-Scrollable Figures List */}
          {!isUser && hasFigures && (
            <div className="flex flex-col gap-2 mt-3 border-t border-neutral-border/20 pt-4">
              <span className="text-[10px] font-bold text-slate-500 font-tech-mono uppercase tracking-widest pl-1">
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
            <div className="flex items-center justify-between mt-4 border-t border-neutral-border/20 pt-3">
              <div className="flex items-center gap-2">
                <ExportButton messageId={message.id} />
              </div>
              <span className="text-[9px] font-tech-mono text-slate-500 font-bold select-none uppercase">
                {message.created_at ? new Date(message.created_at).toLocaleTimeString() : ''}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
