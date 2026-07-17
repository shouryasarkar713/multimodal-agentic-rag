import React, { useState } from 'react';
import { FileText, Trash2, Image as ImageIcon, CheckCircle2, Loader2, XCircle, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { Document } from '../lib/types';
import { api } from '../lib/api';

interface DocumentListProps {
  documents: Document[];
  onDelete: (id: string) => Promise<void>;
  onChatAbout: (docId: string) => void;
  onOpenFigure: (imagePath: string, caption: string, pageNumber: number, documentId: string, chunkId: string) => void;
}

export function DocumentList({
  documents,
  onDelete,
  onChatAbout,
  onOpenFigure,
}: DocumentListProps) {
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);
  const [figures, setFigures] = useState<any[]>([]);
  const [loadingFigures, setLoadingFigures] = useState<boolean>(false);

  const handleToggleExpand = async (docId: string) => {
    if (expandedDocId === docId) {
      setExpandedDocId(null);
      setFigures([]);
      return;
    }

    setExpandedDocId(docId);
    setLoadingFigures(true);
    try {
      const res = await api.getDocumentFigures(docId);
      setFigures(res.figures || []);
    } catch (err) {
      console.error('Failed to load figures:', err);
    } finally {
      setLoadingFigures(false);
    }
  };

  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'ready':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-green-500/5 text-green-400 border border-green-500/20 font-tech-mono text-[9px] font-bold uppercase tracking-wider">
            <CheckCircle2 className="w-2.5 h-2.5" /> Ready
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-yellow-500/5 text-yellow-400 border border-yellow-500/20 font-tech-mono text-[9px] font-bold uppercase tracking-wider animate-pulse">
            <Loader2 className="w-2.5 h-2.5 animate-spin" /> Ingesting
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-red-500/5 text-red-400 border border-red-500/20 font-tech-mono text-[9px] font-bold uppercase tracking-wider">
            <XCircle className="w-2.5 h-2.5" /> Error
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-slate-500/5 text-slate-400 border border-slate-500/20 font-tech-mono text-[9px] font-bold uppercase tracking-wider">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="w-full flex flex-col border border-neutral-border bg-surface rounded-sm overflow-hidden font-sans">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[700px]">
          <thead>
            <tr className="border-b border-neutral-border bg-background/45 font-tech-mono text-[9px] uppercase tracking-widest text-slate-500 font-bold">
              <th className="py-3 px-4 w-12 text-center"></th>
              <th className="py-3 px-4">Title / Filename</th>
              <th className="py-3 px-4">Authors</th>
              <th className="py-3 px-4">Pages</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Uploaded</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-border/25">
            {documents.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-600 font-tech-mono text-xs uppercase tracking-wider font-semibold italic">
                  No documents indexed in corpus.
                </td>
              </tr>
            ) : (
              documents.map((doc) => {
                const isExpanded = expandedDocId === doc.id;
                return (
                  <React.Fragment key={doc.id}>
                    {/* Main Row */}
                    <tr className={`hover:bg-background/20 transition-colors ${isExpanded ? 'bg-background/30' : ''}`}>
                      <td className="py-3 px-4 text-center">
                        {doc.status === 'ready' ? (
                          <button
                            onClick={() => handleToggleExpand(doc.id)}
                            className="p-1 rounded-sm hover:bg-background text-slate-500 hover:text-slate-200 transition-colors border border-transparent hover:border-neutral-border/30"
                            title={isExpanded ? 'Collapse Figures' : 'Expand Figures'}
                          >
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        ) : (
                          <div className="w-4 h-4" />
                        )}
                      </td>
                      <td className="py-3 px-4 font-medium max-w-xs sm:max-w-sm md:max-w-md">
                        <div className="flex flex-col min-w-0">
                          {doc.title ? (
                            <>
                              <span className="text-xs font-bold text-slate-200 font-editorial-serif truncate leading-normal">{doc.title}</span>
                              <span className="text-[10px] text-slate-500 font-tech-mono truncate mt-0.5">{doc.filename}</span>
                            </>
                          ) : (
                            <span className="text-xs font-bold text-slate-200 font-editorial-serif truncate leading-normal">{doc.filename}</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-400 font-grotesk-sans max-w-[150px] truncate">
                        {doc.authors && doc.authors.length > 0 ? doc.authors.join(', ') : '—'}
                      </td>
                      <td className="py-3 px-4 text-xs font-tech-mono text-slate-400">
                        {doc.num_pages || '—'}
                      </td>
                      <td className="py-3 px-4">
                        {getStatusDisplay(doc.status)}
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-450 font-tech-mono">
                        {doc.created_at ? new Date(doc.created_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric'
                        }) : '—'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {doc.status === 'ready' && (
                            <button
                              onClick={() => onChatAbout(doc.id)}
                              className="px-2.5 py-1 bg-background hover:bg-background/80 border border-neutral-border hover:border-primary/50 text-[9px] font-bold font-tech-mono uppercase tracking-wider text-slate-350 hover:text-primary transition-all duration-150 rounded-sm"
                            >
                              Chat
                            </button>
                          )}
                          <button
                            onClick={() => {
                              onDelete(doc.id);
                            }}
                            className="p-1 rounded-sm border border-neutral-border text-slate-500 hover:text-red-400 hover:border-red-500/20 hover:bg-red-500/5 transition-all duration-150"
                            title="Delete document"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* Expanded Drawer (Figures list) */}
                    {isExpanded && (
                      <tr>
                        <td colSpan={7} className="p-0 bg-background/20">
                          <div className="p-5 border-b border-neutral-border/25 flex flex-col gap-3">
                            <span className="text-[9px] uppercase font-bold text-slate-500 font-tech-mono tracking-widest pl-1 block">
                              Extracted Visual Figures & Graphics
                            </span>

                            {loadingFigures ? (
                              <div className="flex items-center gap-2 text-xs text-slate-500 font-tech-mono uppercase tracking-widest py-3 pl-1">
                                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                                Loading document figures...
                              </div>
                            ) : figures.length === 0 ? (
                              <div className="text-slate-550 text-xs py-4 font-semibold font-tech-mono uppercase tracking-wide">
                                No figures extracted from this document.
                              </div>
                            ) : (
                              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
                                {figures.map((fig) => (
                                  <div
                                    key={fig.chunk_id}
                                    className="relative aspect-video rounded-sm border border-neutral-border bg-slate-950 overflow-hidden cursor-pointer hover:border-primary/60 transition-all duration-150 group/fig"
                                    onClick={() => onOpenFigure(fig.image_url, fig.caption, fig.page_number, doc.id, fig.chunk_id)}
                                  >
                                    {/* Thumbnail */}
                                    <img
                                      src={`${process.env.NEXT_PUBLIC_API_URL ? process.env.NEXT_PUBLIC_API_URL.replace('/api', '') : 'http://localhost:8000'}${fig.image_url}`}
                                      alt={fig.caption || 'Extracted Figure'}
                                      className="w-full h-full object-cover group-hover/fig:scale-[1.02] transition-transform duration-150"
                                    />
                                    <div className="absolute bottom-0 inset-x-0 bg-slate-950/90 p-1 border-t border-neutral-border/40 text-[8px] text-slate-400 truncate font-tech-mono uppercase tracking-wide">
                                      PAGE {fig.page_number}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
