'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileText, MessageSquare, ArrowRight, BookOpen, Layers, Send, Sparkles, X } from 'lucide-react';
import { useDocuments } from '../hooks/useDocuments';
import { useChatContext } from '../context/ChatContext';
import { DocumentUploader } from '../components/DocumentUploader';
import { DocumentList } from '../components/DocumentList';

export default function Dashboard() {
  const router = useRouter();
  const { documents, uploading, error, setError, uploadFile, deleteDoc } = useDocuments();
  const { sessions, createNewSession, submitQuery, setSelectedDocumentIds } = useChatContext();
  const [quickQuery, setQuickQuery] = React.useState('');
  const [lightboxFig, setLightboxFig] = useState<{ url: string; caption: string; page: number; docId: string } | null>(null);

  const readyDocsCount = documents.filter((d) => d.status === 'ready').length;
  const totalPages = documents.reduce((sum, d) => sum + (d.total_pages || 0), 0);

  const handleQuickChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickQuery.trim()) return;

    // Create a new session, set query, submit, and redirect
    const newSessionId = await createNewSession(quickQuery.substring(0, 30));
    if (newSessionId) {
      submitQuery(quickQuery);
      router.push('/chat');
    }
  };

  const handleOpenFigure = (imageUrl: string, caption: string, pageNumber: number, documentId: string) => {
    const serverBaseUrl = process.env.NEXT_PUBLIC_API_URL
      ? process.env.NEXT_PUBLIC_API_URL.replace('/api', '')
      : 'http://localhost:8000';
    setLightboxFig({
      url: imageUrl.startsWith('http') ? imageUrl : `${serverBaseUrl}${imageUrl}`,
      caption,
      page: pageNumber,
      docId: documentId
    });
  };

  const handleChatAboutDocument = async (docId: string) => {
    const doc = documents.find((d) => d.id === docId);
    const title = doc ? `Chat: ${doc.title || doc.filename}` : undefined;
    await createNewSession(title, [docId]);
    router.push('/chat');
  };

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto flex flex-col gap-8 relative font-sans">
      {/* Page Header with Running Lab Tally Annotation */}
      <div className="border-b border-neutral-border pb-4">
        <h1 className="font-bold text-2xl md:text-3xl text-slate-100 font-editorial-serif tracking-tight">
          Welcome to <span className="text-primary font-editorial-serif">Research Copilot</span>
        </h1>
        
        {/* Integrated inline stats summary ledger replacing 4-box card KPI row */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-3 text-[10px] font-bold font-tech-mono uppercase tracking-wider text-slate-400">
          <span>INDEXED PAPERS: <span className="text-slate-200">{documents.length}</span></span>
          <span className="w-px h-3.5 bg-neutral-border/40 hidden sm:inline"></span>
          <span>READY CHUNKS: <span className="text-slate-200">{readyDocsCount} INGESTED</span></span>
          <span className="w-px h-3.5 bg-neutral-border/40 hidden sm:inline"></span>
          <span>TOTAL PAGES: <span className="text-slate-200">{totalPages}</span></span>
          <span className="w-px h-3.5 bg-neutral-border/40 hidden sm:inline"></span>
          <span>ACTIVE SESSIONS: <span className="text-slate-200">{sessions.length}</span></span>
        </div>
      </div>

      {/* Main Asymmetric Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column (72%): Recent Indexed Papers Logbook Ledger */}
        <div className="lg:col-span-8 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-neutral-border/45 pb-2">
            <h3 className="font-bold text-[10px] uppercase text-slate-400 font-tech-mono tracking-widest">
              Recent Indexed Papers
            </h3>
            <button
              onClick={() => router.push('/documents')}
              className="text-[9px] font-bold text-slate-450 hover:text-primary flex items-center gap-1 transition-colors uppercase tracking-widest bg-background border border-neutral-border px-2.5 py-1 rounded-sm hover:border-primary/50 font-tech-mono"
            >
              Library <ArrowRight className="w-3.5 h-3.5 text-primary" />
            </button>
          </div>

          <DocumentList
            documents={documents.slice(0, 5)}
            onDelete={deleteDoc}
            onChatAbout={handleChatAboutDocument}
            onOpenFigure={handleOpenFigure}
          />
        </div>

        {/* Right Column (28%): Ingest & Quick Launcher Actions */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          {/* Document Ingestion Zone */}
          <div className="bg-surface border border-neutral-border p-5 rounded-sm flex flex-col gap-4">
            <h3 className="font-bold text-[10px] uppercase text-slate-400 font-tech-mono tracking-widest border-b border-neutral-border/30 pb-2">
              Ingest Document
            </h3>
            <DocumentUploader
              onUpload={uploadFile}
              uploading={uploading}
              error={error}
              setError={setError}
            />
          </div>

          {/* Quick Launcher */}
          <div className="bg-surface border border-neutral-border p-5 rounded-sm flex flex-col gap-4">
            <h3 className="font-bold text-[10px] uppercase text-slate-400 font-tech-mono tracking-widest border-b border-neutral-border/30 pb-2">
              Quick Launcher
            </h3>
            <form onSubmit={handleQuickChatSubmit} className="relative font-sans">
              <input
                type="text"
                value={quickQuery}
                onChange={(e) => setQuickQuery(e.target.value)}
                placeholder="QueryIndexedPapers..."
                className="w-full pl-3.5 pr-10 py-3 bg-slate-950/80 border border-neutral-border rounded-sm text-xs font-semibold text-slate-200 placeholder-slate-650 focus:outline-none focus:border-primary transition-colors font-tech-mono"
              />
              <button
                type="submit"
                className="absolute right-2 top-2 p-1.5 rounded-sm bg-background border border-neutral-border text-slate-400 hover:text-primary hover:border-primary/50 transition-colors"
                title="Launch Chat"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

        </div>
      </div>

      {/* Shared Gallery Lightbox */}
      {lightboxFig && (
        <div className="fixed inset-0 bg-slate-950/85 z-50 flex items-center justify-center p-4">
          <button
            onClick={() => setLightboxFig(null)}
            className="absolute top-4 right-4 p-2 rounded-sm bg-surface text-slate-450 hover:text-slate-100 hover:bg-background transition-colors border border-neutral-border"
          >
            <X className="w-5 h-5" />
          </button>
          
          <div className="w-full max-w-4xl flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-200 font-sans">
            <div className="relative aspect-video rounded-sm bg-slate-950 overflow-hidden border border-neutral-border flex items-center justify-center">
              <img
                src={lightboxFig.url}
                alt={lightboxFig.caption}
                className="max-h-[70vh] max-w-full object-contain"
              />
            </div>
            
            <div className="bg-surface border border-neutral-border p-4 rounded-sm max-w-2xl w-full mx-auto flex flex-col gap-3">
              <div className="flex items-center justify-between gap-3">
                <h4 className="font-bold text-[9px] font-tech-mono text-slate-400 uppercase tracking-widest">
                  /figure_detail
                </h4>
                <span className="text-[9px] font-tech-mono font-bold text-primary bg-background/20 px-2 py-0.5 rounded-sm border border-primary/20">
                  PAGE {lightboxFig.page}
                </span>
              </div>
              <p className="text-xs text-slate-200 font-editorial-serif leading-relaxed italic font-semibold">
                {lightboxFig.caption || 'No caption available.'}
              </p>
              
              <button
                onClick={async () => {
                  const title = `Explain Figure (Page ${lightboxFig.page})`;
                  await createNewSession(title, [lightboxFig.docId]);
                  sessionStorage.setItem('auto_submit_query', `explain figure: ${lightboxFig.caption || 'figure'}`);
                  setLightboxFig(null);
                  router.push('/chat');
                }}
                className="mt-1 w-full py-2 px-4 rounded-sm bg-background border border-neutral-border hover:border-primary/50 hover:text-primary text-slate-350 font-bold font-tech-mono text-xs uppercase tracking-wider transition-colors"
              >
                Explain this figure
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
