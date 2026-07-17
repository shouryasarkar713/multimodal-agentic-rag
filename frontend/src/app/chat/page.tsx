'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { Send, Loader2, Sparkles, Filter, CheckSquare, Square, FileText } from 'lucide-react';
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
  const [mobileScoperOpen, setMobileScoperOpen] = useState(false);

  return (
    <div className="flex h-screen bg-background text-slate-100 font-sans relative overflow-hidden">
      {/* Permanent Left Scoping Panel - Option 2B & Functional default unchecked list */}
      <div className="w-80 border-r border-neutral-border bg-surface flex flex-col shrink-0 hidden md:flex">
        <div className="h-16 px-4 border-b border-neutral-border flex items-center justify-between">
          <span className="text-[10px] uppercase font-bold text-slate-400 font-tech-mono tracking-widest">
            Document Scope
          </span>
          <span className="text-[9px] font-tech-mono font-bold text-primary bg-background/25 px-1.5 py-0.5 rounded-sm border border-primary/25">
            {selectedDocumentIds.length} ACTIVE
          </span>
        </div>
        
        {/* Document Selection List */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between font-tech-mono text-[9px] uppercase tracking-wider font-bold border-b border-neutral-border/20 pb-2">
            <button
              onClick={() => setSelectedDocumentIds(readyDocuments.map(d => d.id))}
              className="text-slate-500 hover:text-primary transition-colors"
            >
              Select All
            </button>
            <button
              onClick={() => setSelectedDocumentIds([])}
              className="text-slate-500 hover:text-primary transition-colors"
            >
              Clear All
            </button>
          </div>

          {readyDocuments.length === 0 ? (
            <div className="text-[9px] text-slate-655 font-tech-mono uppercase tracking-wider leading-relaxed py-4">
              NO INDEXED PAPERS IN DATABASE. USE THE UPLOADER ON THE HOME PAGE TO START.
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {readyDocuments.map((doc) => {
                const isSelected = selectedDocumentIds.includes(doc.id);
                return (
                  <div
                    key={doc.id}
                    onClick={() => toggleDocumentSelection(doc.id)}
                    className={`flex items-start gap-2.5 p-2 rounded-sm border cursor-pointer select-none transition-all duration-150 ${
                      isSelected
                        ? 'bg-primary/5 border-primary/30 text-slate-100'
                        : 'border-neutral-border/25 hover:border-neutral-border/50 text-slate-450 hover:text-slate-200'
                    }`}
                  >
                    <div className="mt-0.5">
                      {isSelected ? (
                        <div className="w-3.5 h-3.5 rounded-sm border border-primary bg-primary flex items-center justify-center text-background text-[9px] font-bold">✓</div>
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-sm border border-neutral-border/40" />
                      )}
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="text-[11px] font-bold truncate font-editorial-serif leading-tight">
                        {doc.title || doc.filename}
                      </span>
                      <span className="text-[9px] font-tech-mono truncate mt-0.5 opacity-80">
                        {doc.filename}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Mobile Drawer Overlay for Scoper */}
      {mobileScoperOpen && (
        <div className="fixed inset-0 z-40 md:hidden flex">
          <div className="fixed inset-0 bg-slate-950/80" onClick={() => setMobileScoperOpen(false)} />
          <div className="relative w-80 bg-surface border-r border-neutral-border flex flex-col h-full z-50 p-4 animate-in slide-in-from-left duration-200">
            <div className="flex items-center justify-between border-b border-neutral-border pb-3 mb-4">
              <span className="text-[10px] uppercase font-bold text-slate-400 font-tech-mono tracking-widest">
                Document Scope
              </span>
              <button
                onClick={() => setMobileScoperOpen(false)}
                className="text-[9px] font-tech-mono text-slate-455 hover:text-slate-200 border border-neutral-border px-2 py-0.5 rounded-sm"
              >
                Close
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto flex flex-col gap-3">
              <div className="flex items-center justify-between font-tech-mono text-[9px] uppercase tracking-wider font-bold border-b border-neutral-border/20 pb-2">
                <button
                  onClick={() => setSelectedDocumentIds(readyDocuments.map(d => d.id))}
                  className="text-slate-500 hover:text-primary"
                >
                  Select All
                </button>
                <button
                  onClick={() => setSelectedDocumentIds([])}
                  className="text-slate-500 hover:text-primary"
                >
                  Clear All
                </button>
              </div>

              {readyDocuments.length === 0 ? (
                <div className="text-[9px] text-slate-600 font-tech-mono uppercase tracking-wider leading-relaxed py-4">
                  NO INDEXED PAPERS IN DATABASE.
                </div>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {readyDocuments.map((doc) => {
                    const isSelected = selectedDocumentIds.includes(doc.id);
                    return (
                      <div
                        key={doc.id}
                        onClick={() => toggleDocumentSelection(doc.id)}
                        className={`flex items-start gap-2.5 p-2 rounded-sm border cursor-pointer select-none ${
                          isSelected
                            ? 'bg-primary/5 border-primary/30 text-slate-100'
                            : 'border-neutral-border/25 text-slate-450'
                        }`}
                      >
                        <div className="mt-0.5">
                          {isSelected ? (
                            <div className="w-3.5 h-3.5 rounded-sm border border-primary bg-primary flex items-center justify-center text-background text-[9px] font-bold">✓</div>
                          ) : (
                            <div className="w-3.5 h-3.5 rounded-sm border border-neutral-border/40" />
                          )}
                        </div>
                        <div className="flex flex-col min-w-0">
                          <span className="text-[11px] font-bold truncate font-editorial-serif leading-tight">
                            {doc.title || doc.filename}
                          </span>
                          <span className="text-[9px] font-tech-mono truncate mt-0.5 opacity-80">
                            {doc.filename}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Right Chat Panel */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Upper Context Header */}
        <div className="h-16 px-6 border-b border-neutral-border bg-surface flex items-center justify-between shrink-0">
          <div>
            <h2 className="font-bold text-sm text-slate-200 font-editorial-serif uppercase tracking-wider">
              Research Workspace
            </h2>
            <p className="text-[9px] text-slate-500 font-tech-mono uppercase tracking-widest mt-0.5">
              {messages.length} messages in conversation
            </p>
          </div>

          <button
            onClick={() => setMobileScoperOpen(!mobileScoperOpen)}
            className="md:hidden flex items-center gap-1.5 px-3 py-1.5 rounded-sm border border-neutral-border bg-background hover:bg-surface text-[10px] font-bold font-tech-mono uppercase tracking-wider text-slate-350 transition-colors"
          >
            <span>Scope: {selectedDocumentIds.length}</span>
          </button>
        </div>

        {/* Conversation Viewer Pane */}
        <div className="flex-1 overflow-y-auto select-text scrollbar-thin">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col justify-end p-6 md:p-8 max-w-4xl mx-auto">
              <div className="border-l border-neutral-border pl-6 py-4 mb-16 flex flex-col gap-2">
                <span className="text-[9px] font-tech-mono font-bold text-slate-500 uppercase tracking-widest">
                  Active Workspace initialized
                </span>
                <h3 className="font-bold text-lg text-slate-200 font-editorial-serif">
                  Awaiting query submission
                </h3>
                <p className="text-xs text-slate-450 max-w-xl font-sans leading-relaxed">
                  Enter a research question below. The assistant will retrieve and analyze relevant text, tables, and figures from your scoped documents.
                </p>
              </div>
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
            
            {/* Inline footnote suggested queries (Option 2B requirement) */}
            {messages.length === 0 && (
              <div className="text-[10px] font-tech-mono text-slate-500 flex flex-wrap gap-x-4 gap-y-1.5 uppercase font-bold tracking-wide border-b border-neutral-border/20 pb-3 mb-1">
                <span className="text-slate-655">Suggested queries:</span>
                {suggestions.map((s, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSuggestionClick(s)}
                    className="hover:text-primary transition-colors text-left"
                  >
                    [{idx + 1}] {s.replace(/\.$/, '')}
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
    </div>
  );
}
