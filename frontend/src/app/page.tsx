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
    <div className="p-6 md:p-8 max-w-7xl mx-auto flex flex-col gap-8">
      {/* Page Header */}
      <div>
        <h1 className="font-extrabold text-2xl md:text-3xl text-slate-100 tracking-tight">
          Welcome back to Research Copilot
        </h1>
        <p className="text-xs md:text-sm text-slate-400 mt-1 font-semibold">
          Upload technical papers, query schemas or architectures, and run cross-paper comparison checks.
        </p>
      </div>

      {/* Metrics Card Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 flex items-center gap-4 hover:border-slate-700/60 transition-all duration-200">
          <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Total Papers</div>
            <div className="text-lg font-bold text-slate-100 mt-0.5">{documents.length}</div>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 flex items-center gap-4 hover:border-slate-700/60 transition-all duration-200">
          <div className="p-3 rounded-xl bg-green-500/10 text-green-400 border border-green-500/20">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Ready Chunks</div>
            <div className="text-lg font-bold text-slate-100 mt-0.5">{readyDocsCount} Ingested</div>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 flex items-center gap-4 hover:border-slate-700/60 transition-all duration-200">
          <div className="p-3 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Total Pages</div>
            <div className="text-lg font-bold text-slate-100 mt-0.5">{totalPages} pages</div>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 flex items-center gap-4 hover:border-slate-700/60 transition-all duration-200">
          <div className="p-3 rounded-xl bg-pink-500/10 text-pink-400 border border-pink-500/20">
            <MessageSquare className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Chat Sessions</div>
            <div className="text-lg font-bold text-slate-100 mt-0.5">{sessions.length} sessions</div>
          </div>
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload & Quick Chat Side Panels */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          {/* Document Ingestion Zone */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 flex flex-col gap-4">
            <h3 className="font-extrabold text-xs uppercase text-slate-400 tracking-wider">
              Ingest Document
            </h3>
            <DocumentUploader
              onUpload={uploadFile}
              uploading={uploading}
              error={error}
              setError={setError}
            />
          </div>

          {/* Quick Launcher Launcher */}
          <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 flex flex-col gap-4">
            <h3 className="font-extrabold text-xs uppercase text-slate-400 tracking-wider">
              Quick Query Launcher
            </h3>
            <form onSubmit={handleQuickChatSubmit} className="relative">
              <input
                type="text"
                value={quickQuery}
                onChange={(e) => setQuickQuery(e.target.value)}
                placeholder="Ask something about your papers..."
                className="w-full pl-3 pr-10 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-semibold text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 transition-colors"
              />
              <button
                type="submit"
                className="absolute right-1.5 top-1.5 p-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
                title="Launch Chat"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </div>

        {/* Recent Uploads Table Panel */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-extrabold text-xs uppercase text-slate-400 tracking-wider pl-1">
              Recent Documents Ingested
            </h3>
            <button
              onClick={() => router.push('/documents')}
              className="text-[10px] font-extrabold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors uppercase tracking-wider"
            >
              Library <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <DocumentList
            documents={documents.slice(0, 5)}
            onDelete={deleteDoc}
            onChatAbout={handleChatAboutDocument}
            onOpenFigure={handleOpenFigure}
          />
        </div>
      </div>

      {/* Shared Gallery Lightbox */}
      {lightboxFig && (
        <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <button
            onClick={() => setLightboxFig(null)}
            className="absolute top-4 right-4 p-2 rounded-xl bg-slate-900 text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors border border-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
          
          <div className="w-full max-w-4xl flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="relative aspect-video rounded-2xl bg-slate-900 overflow-hidden border border-slate-800 flex items-center justify-center">
              <img
                src={lightboxFig.url}
                alt={lightboxFig.caption}
                className="max-h-[70vh] max-w-full object-contain"
              />
            </div>
            
            <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl max-w-2xl mx-auto flex flex-col gap-3">
              <div className="flex items-center justify-between gap-3">
                <h4 className="font-extrabold text-xs text-slate-200">
                  FIGURE DETAIL
                </h4>
                <span className="text-[10px] font-mono font-bold text-indigo-400 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-900/50">
                  Page {lightboxFig.page}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-semibold leading-relaxed">
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
                className="mt-1 w-full py-2 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-extrabold text-xs transition-colors flex items-center justify-center gap-1.5 shadow-lg shadow-indigo-600/10"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-200" />
                Explain this figure
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
