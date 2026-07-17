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
    <div className="p-6 md:p-8 max-w-7xl mx-auto flex flex-col gap-8 relative">
      {/* Background Ambient Glow Refractions */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-500/5 rounded-full blur-[100px] pointer-events-none -z-10"></div>
      <div className="absolute bottom-10 right-10 w-[450px] h-[450px] bg-purple-500/5 rounded-full blur-[120px] pointer-events-none -z-10"></div>

      {/* Page Header */}
      <div>
        <h1 className="font-extrabold text-2xl md:text-3xl text-slate-100 tracking-tight flex items-center gap-2">
          Welcome back to <span className="text-indigo-400 neon-text">Research Copilot</span>
        </h1>
        <p className="text-xs md:text-sm text-slate-400 mt-1.5 font-semibold">
          Upload technical papers, query schemas or architectures, and run cross-paper comparison checks.
        </p>
      </div>

      {/* Metrics Card Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="glass-card rounded-2xl p-5 flex items-center gap-4 hover:border-indigo-500/40 transition-all duration-300 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/10 rounded-full blur-xl -mr-10 -mt-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 group-hover:scale-110 transition-transform duration-300">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Total Papers</div>
            <div className="text-lg font-bold text-slate-100 mt-0.5 font-mono">{documents.length}</div>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="glass-card rounded-2xl p-5 flex items-center gap-4 hover:border-green-500/40 transition-all duration-300 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-green-500/10 rounded-full blur-xl -mr-10 -mt-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div className="p-3 rounded-xl bg-green-500/10 text-green-400 border border-green-500/20 group-hover:scale-110 transition-transform duration-300">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Ready Chunks</div>
            <div className="text-lg font-bold text-slate-100 mt-0.5 font-mono">{readyDocsCount} Ingested</div>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="glass-card rounded-2xl p-5 flex items-center gap-4 hover:border-violet-500/40 transition-all duration-300 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-violet-500/10 rounded-full blur-xl -mr-10 -mt-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div className="p-3 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20 group-hover:scale-110 transition-transform duration-300">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Total Pages</div>
            <div className="text-lg font-bold text-slate-100 mt-0.5 font-mono">{totalPages} pages</div>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="glass-card rounded-2xl p-5 flex items-center gap-4 hover:border-pink-500/40 transition-all duration-300 relative overflow-hidden group border-indigo-500/20 shadow-neon">
          <div className="absolute top-0 right-0 w-24 h-24 bg-pink-500/10 rounded-full blur-xl -mr-10 -mt-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          <div className="p-3 rounded-xl bg-pink-500/10 text-pink-400 border border-pink-500/20 group-hover:scale-110 transition-transform duration-300">
            <MessageSquare className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider font-semibold">Chat Sessions</div>
            <div className="text-lg font-bold text-slate-100 mt-0.5 font-mono">{sessions.length} sessions</div>
          </div>
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload & Quick Chat Side Panels */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          {/* Document Ingestion Zone */}
          <div className="glass-panel p-5 rounded-2xl flex flex-col gap-4 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-full blur-xl -mr-6 -mt-6"></div>
            <h3 className="font-extrabold text-xs uppercase text-slate-350 tracking-wider flex items-center gap-1.5 pl-1">
              <Layers className="w-3.5 h-3.5 text-indigo-400" /> Ingest Document
            </h3>
            <DocumentUploader
              onUpload={uploadFile}
              uploading={uploading}
              error={error}
              setError={setError}
            />
          </div>

          {/* Quick Launcher Launcher */}
          <div className="glass-panel p-5 rounded-2xl flex flex-col gap-4 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full blur-xl -mr-6 -mt-6"></div>
            <h3 className="font-extrabold text-xs uppercase text-slate-350 tracking-wider flex items-center gap-1.5 pl-1">
              <Sparkles className="w-3.5 h-3.5 text-purple-400 animate-pulse" /> Quick Query Launcher
            </h3>
            <form onSubmit={handleQuickChatSubmit} className="relative">
              <input
                type="text"
                value={quickQuery}
                onChange={(e) => setQuickQuery(e.target.value)}
                placeholder="Ask something about your papers..."
                className="w-full pl-3.5 pr-10 py-3 bg-slate-950/70 border border-slate-800 rounded-xl text-xs font-semibold text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 transition-colors"
              />
              <button
                type="submit"
                className="absolute right-2 top-2 p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-lg shadow-indigo-600/20"
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
            <h3 className="font-extrabold text-xs uppercase text-slate-350 tracking-wider pl-1 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-indigo-400" /> Recent Documents Ingested
            </h3>
            <button
              onClick={() => router.push('/documents')}
              className="text-[10px] font-extrabold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors uppercase tracking-wider bg-indigo-500/5 border border-indigo-500/10 px-2.5 py-1 rounded-lg hover:border-indigo-550/20"
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
