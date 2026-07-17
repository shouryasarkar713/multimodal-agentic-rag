'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Library, Upload, Plus, X, Search } from 'lucide-react';
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
    <div className="p-6 md:p-8 max-w-7xl mx-auto flex flex-col gap-8 relative font-sans">
      {/* Page Header Actions */}
      <div className="flex items-center justify-between gap-4 flex-wrap border-b border-neutral-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Library className="w-5 h-5 text-primary" />
            <h1 className="font-bold text-2xl text-slate-100 font-editorial-serif tracking-tight">
              Document Library
            </h1>
          </div>
          <p className="text-xs text-slate-455 mt-1 font-tech-mono uppercase tracking-wide">
            /manage_research_corpus_active
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-sm bg-background border border-neutral-border hover:border-primary/50 text-slate-200 hover:text-primary font-bold font-tech-mono text-xs uppercase tracking-wider transition-all duration-150"
        >
          <Plus className="w-4 h-4" /> Add Paper
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="relative max-w-md w-full font-sans">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter by title, author, or filename..."
          className="w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-neutral-border rounded-sm text-xs font-semibold text-slate-200 placeholder-slate-650 focus:outline-none focus:border-primary transition-colors font-tech-mono"
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
        <div className="fixed inset-0 bg-slate-950/80 z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-xl rounded-sm border border-neutral-border bg-surface p-6 relative flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Upload className="w-4.5 h-4.5 text-primary" />
                <h3 className="font-bold text-sm text-slate-100 font-editorial-serif">
                  Ingest New Research Paper
                </h3>
              </div>
              <button
                onClick={() => {
                  setError(null);
                  setShowUploadModal(false);
                }}
                className="p-1 rounded-sm text-slate-500 hover:bg-background hover:text-slate-200 transition-colors border border-transparent hover:border-neutral-border/30"
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
                className="px-4 py-1.5 rounded-sm bg-background border border-neutral-border text-xs font-bold font-tech-mono uppercase tracking-wider text-slate-350 hover:text-primary hover:border-primary/50 transition-colors"
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
