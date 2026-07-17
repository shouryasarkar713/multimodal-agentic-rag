'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Library, Plus, ArrowRight, X, AlertCircle } from 'lucide-react';
import { useDocuments } from '../../hooks/useDocuments';
import { useChatContext } from '../../context/ChatContext';
import { DocumentList } from '../../components/DocumentList';
import { DocumentUploader } from '../../components/DocumentUploader';

export default function DocumentsPage() {
  const router = useRouter();
  const { documents, uploading, error, setError, uploadFile, deleteDoc } = useDocuments();
  const { createNewSession } = useChatContext();
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [lightboxFig, setLightboxFig] = useState<{ url: string; caption: string; page: number; docId: string } | null>(null);

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
    <div className="p-6 md:p-8 max-w-7xl mx-auto flex flex-col gap-6 font-sans relative">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap border-b border-neutral-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Library className="w-5 h-5 text-primary" />
            <h1 className="font-bold text-2xl text-slate-100 font-editorial-serif tracking-tight">
              Document Library
            </h1>
          </div>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-sm bg-background border border-neutral-border hover:border-primary/50 text-slate-200 hover:text-primary font-bold font-tech-mono text-xs uppercase tracking-wider transition-all duration-150"
        >
          <Plus className="w-4 h-4" /> Add Paper
        </button>
      </div>

      {/* Main Document List */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between pl-1">
          <span className="text-[10px] uppercase font-bold text-slate-400 font-tech-mono tracking-widest">
            Indexed Corpus
          </span>
          <span className="text-[9px] font-tech-mono font-bold text-slate-500 uppercase tracking-widest">
            {documents.length} papers registered
          </span>
        </div>

        <DocumentList
          documents={documents}
          onDelete={deleteDoc}
          onChatAbout={handleChatAboutDocument}
          onOpenFigure={handleOpenFigure}
        />
      </div>

      {/* Ingest Modal Overlay */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-slate-950/85 z-50 flex items-center justify-center p-4 select-none">
          <div className="bg-surface border border-neutral-border p-6 rounded-sm max-w-md w-full relative flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-150 font-sans">
            <button
              onClick={() => {
                setShowUploadModal(false);
                setError(null);
              }}
              className="absolute top-4 right-4 p-1 rounded-sm bg-background text-slate-500 hover:text-slate-100 border border-neutral-border hover:border-slate-500 transition-colors"
              title="Close modal"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex flex-col gap-1 border-b border-neutral-border/30 pb-2">
              <h3 className="font-bold text-sm text-slate-200 font-editorial-serif">
                Index New Research Paper
              </h3>
              <p className="text-[9px] font-tech-mono font-bold text-slate-500 uppercase tracking-wider">
                Upload manuscript for RAG parsing
              </p>
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

            {error && (
              <div className="flex items-center gap-2 p-3 border border-red-500/20 bg-red-500/5 text-red-400 text-xs font-bold rounded-sm font-tech-mono uppercase tracking-wider mt-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
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
