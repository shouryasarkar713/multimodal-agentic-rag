'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { Send, Loader2, Sparkles, Filter, CheckSquare, Square } from 'lucide-react';
import { useChatContext } from '../../context/ChatContext';
import { useDocuments } from '../../hooks/useDocuments';
import { ChatMessage } from '../../components/ChatMessage';

export default function ChatPage() {
  const {
    activeSessionId,
    messages,
    sendingMessage,
    selectedDocumentIds,
    setSelectedDocumentIds,
    submitQuery,
    setActiveSessionId,
  } = useChatContext();

  const { documents } = useDocuments();
  const [query, setQuery] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Handle session query parameter from compare page
  const searchParams = useSearchParams();
  useEffect(() => {
    const sessionId = searchParams.get('session');
    if (sessionId && sessionId !== activeSessionId) {
      setActiveSessionId(sessionId);
      // Clean up URL
      window.history.replaceState({}, '', '/chat');
    }
  }, [searchParams, activeSessionId, setActiveSessionId]);

  // Suggestion Prompts
  const suggestions = [
    'Compare the BLEU scores between the models.',
    'Explain Figure 1 in the Transformer paper.',
    'Summarize Section 3.2 (Attention mechanism).',
    'What loss function is utilized for training?',
  ];

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || sendingMessage) return;
    submitQuery(query);
    setQuery('');
  };

  const handleSuggestionClick = (prompt: string) => {
    setQuery(prompt);
  };

  const toggleDocumentSelection = (id: string) => {
    setSelectedDocumentIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((docId) => docId !== id);
      }
      return [...prev, id];
    });
  };

  // Scroll to bottom helper
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, sendingMessage]);

  // Handle auto-submit query from document library figures
  useEffect(() => {
    const autoQuery = sessionStorage.getItem('auto_submit_query');
    if (autoQuery) {
      sessionStorage.removeItem('auto_submit_query');
      submitQuery(autoQuery);
    }
  }, [submitQuery]);

  const readyDocuments = documents.filter((d) => d.status === 'ready');

  return (
    <div className="flex flex-col h-screen bg-background text-slate-100 relative font-sans">
      {/* Upper Context Header */}
      <div className="h-16 px-6 border-b border-neutral-border bg-surface flex items-center justify-between z-10 shrink-0">
        <div className="min-w-0">
          <h2 className="font-bold text-sm text-slate-200 font-editorial-serif uppercase tracking-wider truncate">
            Active Chat Session
          </h2>
          <p className="text-[9px] text-slate-500 font-tech-mono uppercase tracking-widest mt-0.5">
            {messages.length} messages in conversation
          </p>
        </div>

        {/* Dynamic Document Scoper */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm border border-neutral-border bg-background hover:bg-surface text-[10px] font-bold font-tech-mono uppercase tracking-wider text-slate-350 transition-colors"
          >
            <Filter className="w-3.5 h-3.5 text-primary" />
            <span>Scope: {selectedDocumentIds.length === 0 ? 'All Papers' : `${selectedDocumentIds.length} Paper(s)`}</span>
          </button>
          
          {dropdownOpen && (
            <>
              <div className="fixed inset-0 z-20" onClick={() => setDropdownOpen(false)} />
              <div className="absolute right-0 mt-2 w-64 rounded-sm border border-neutral-border bg-surface p-3 z-30 flex flex-col gap-2.5 animate-in fade-in slide-in-from-top-1 duration-150">
                <span className="text-[9px] uppercase font-bold text-slate-550 font-tech-mono tracking-widest pl-1">
                  Scope Query to:
                </span>
                
                {readyDocuments.length === 0 ? (
                  <div className="text-[10px] text-slate-600 font-tech-mono italic p-2">
                    No ready documents available.
                  </div>
                ) : (
                  <div className="flex flex-col gap-1 max-h-48 overflow-y-auto pr-1">
                    {readyDocuments.map((doc) => {
                      const isSelected = selectedDocumentIds.includes(doc.id);
                      return (
                        <div
                          key={doc.id}
                          className="flex items-start gap-2.5 p-2 rounded-sm hover:bg-background cursor-pointer select-none"
                          onClick={() => toggleDocumentSelection(doc.id)}
                        >
                          <div className="mt-0.5 text-primary">
                            {isSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="text-[11px] font-bold text-slate-200 truncate font-editorial-serif">
                              {doc.title || doc.filename}
                            </span>
                            <span className="text-[9px] text-slate-500 font-tech-mono truncate mt-0.5">
                              {doc.filename}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
                
                <div className="border-t border-neutral-border/30 pt-2 flex justify-between font-tech-mono text-[9px] uppercase tracking-wider font-bold">
                  <button
                    onClick={() => setSelectedDocumentIds([])}
                    className="text-slate-500 hover:text-primary px-1.5 py-0.5 border border-neutral-border/20 bg-background rounded-sm"
                  >
                    Clear All
                  </button>
                  <button
                    onClick={() => setDropdownOpen(false)}
                    className="text-primary hover:text-primary-hover px-1.5 py-0.5 border border-primary/20 bg-background rounded-sm"
                  >
                    Done
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Main Conversation Viewer Pane */}
      <div className="flex-1 overflow-y-auto select-text scrollbar-thin">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-6 text-center select-none">
            <div className="p-3 rounded-sm bg-background border border-primary/20 text-primary mb-4">
              <Sparkles className="w-8 h-8" />
            </div>
            <h3 className="font-bold text-md text-slate-200 font-editorial-serif">
              Start a Conversation
            </h3>
            <p className="text-xs text-slate-500 mt-2 max-w-sm font-medium font-grotesk-sans leading-relaxed">
              Select target documents and ask questions. The agent will retrieve text, tables, and figures to draft a verified response.
            </p>
          </div>
        ) : (
          <div className="flex flex-col">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            
            {/* Typing Loader State */}
            {sendingMessage && (
              <div className="flex gap-4 py-6 px-4 md:px-6 bg-surface/10 border-b border-neutral-border/20 justify-start select-none">
                <div className="w-8 h-8 rounded-sm bg-background border border-primary/20 text-primary flex items-center justify-center shrink-0">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
                <div className="flex flex-col gap-2 flex-1 mt-1.5">
                  <span className="text-[9px] font-bold text-primary font-tech-mono uppercase tracking-widest animate-pulse">
                    Copilot is planning and reasoning...
                  </span>
                  {/* Pulsing indicator dots */}
                  <div className="flex items-center gap-1 mt-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary/70 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-primary/70 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-primary/70 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Suggestion Prompt & Input Area */}
      <div className="p-4 md:p-6 border-t border-neutral-border bg-surface shrink-0 select-none">
        <div className="max-w-4xl mx-auto flex flex-col gap-4">
          {/* suggestion pills */}
          {messages.length === 0 && (
            <div className="flex flex-wrap gap-2">
              {suggestions.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestionClick(s)}
                  className="px-3 py-1.5 rounded-sm border border-neutral-border hover:border-slate-550 bg-background hover:bg-surface text-[9px] font-bold font-tech-mono text-slate-500 hover:text-primary text-left transition-all duration-150 uppercase tracking-wide"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Form input */}
          <form onSubmit={handleSend} className="relative font-sans">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask anything about the scoped papers..."
              className="w-full pl-4 pr-12 py-3 bg-background border border-neutral-border rounded-sm text-xs md:text-sm font-semibold text-slate-200 placeholder-slate-650 focus:outline-none focus:border-primary transition-colors font-tech-mono"
              disabled={sendingMessage}
            />
            <button
              type="submit"
              disabled={sendingMessage || !query.trim()}
              className="absolute right-2 top-2 p-1.5 rounded-sm bg-background border border-neutral-border hover:border-primary/50 text-slate-500 hover:text-primary disabled:text-slate-750 disabled:border-neutral-border/20 transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
