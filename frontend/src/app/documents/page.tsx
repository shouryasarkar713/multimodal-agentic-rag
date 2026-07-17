'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileText, Search, Library, Upload, Plus, X, ZoomIn, Sparkles } from 'lucide-react';
import { useDocuments } from '../../hooks/useDocuments';
import { useChatContext } from '../../context/ChatContext';
import { DocumentList } from '../../components/DocumentList';
import { DocumentUploader } from '../../components/DocumentUploader';

export default function LibraryPage() {
  const router = useRouter();
  const { documents, uploading, error, setError, uploadFile, deleteDoc } = useDocuments();
  const { setSelectedDocumentIds, createNewSession } = useChatContext();
  const [searchQuery, setSearchQuery] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [lightboxFig, setLightboxFig] = useState<{ url: string; caption: string; page: number; docId: string } | null>(null);

  const handleChatAboutDocument = async (docId: string) => {
    const doc = documents.find((d) => d.id === docId);
    const title = doc ? `Chat: ${doc.title || doc.filename}` : undefined;
    await createNewSession(title, [docId]);
    router.push('/chat');
  };

  const filteredDocs = documents.filter((doc) => {
    const q = searchQuery.toLowerCase();
    const titleMatch = doc.title?.toLowerCase().includes(q) || false;
    const filenameMatch = doc.filename.toLowerCase().includes(q);
    const authorsMatch = doc.authors?.some((a) => a.toLowerCase().includes(q)) || false;
    return titleMatch || filenameMatch || authorsMatch;
  });

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

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto flex flex-col gap-8 relative">
      {/* Page Header Actions */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <Library className="w-5 h-5 text-indigo-400" />
            <h1 className="font-extrabold text-2xl text-slate-100 tracking-tight">
              Document Library
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-semibold">
            Manage your research corpus, inspect extracted tables or diagrams, and start queries.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-extrabold text-xs shadow-lg transition-all duration-150"
        >
          <Plus className="w-4 h-4" /> Add Paper
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="relative max-w-md w-full">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter by title, author, or filename..."
          className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs font-semibold text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 transition-colors"
        />
        <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
      </div>

      {/* Complete Documents List */}
      <DocumentList
        documents={filteredDocs}
        onDelete={deleteDoc}
        onChatAbout={handleChatAboutDocument}
        onOpenFigure={handleOpenFigure}
      />

      {/* Ingestion Upload Overlay Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl p-6 relative flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Upload className="w-4.5 h-4.5 text-indigo-400" />
                <h3 className="font-extrabold text-sm text-slate-100">
                  Ingest New Research Paper
                </h3>
              </div>
              <button
                onClick={() => {
                  setError(null);
                  setShowUploadModal(false);
                }}
                className="p-1 rounded-lg text-slate-500 hover:bg-slate-800 hover:text-slate-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <DocumentUploader
              onUpload={async (file) => {
                await uploadFile(file);
                setShowUploadModal(false);
              }}
              uploading={uploading}
              error={error}
              setError={setError}
            />

            <div className="flex justify-end gap-2 mt-2">
              <button
                onClick={() => {
                  setError(null);
                  setShowUploadModal(false);
                }}
                className="px-4 py-2 rounded-lg bg-slate-800 text-xs font-bold text-slate-300 hover:bg-slate-700 transition-colors"
                disabled={uploading}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

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
                  // Create a new session with the document selected in scope
                  await createNewSession(title, [lightboxFig.docId]);
                  // Store query to submit on Chat page load
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
