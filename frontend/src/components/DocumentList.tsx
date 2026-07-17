import React, { useState } from 'react';
import { Trash2, ChevronDown, ChevronUp, Image as ImageIcon, Loader2 } from 'lucide-react';
import { Document } from '../lib/types';
import { useFigures } from '../hooks/useFigures';

interface DocumentListProps {
  documents: Document[];
  onDelete: (id: string) => Promise<void>;
  onChatAbout: (id: string) => void;
  onOpenFigure: (imageUrl: string, caption: string, pageNumber: number, documentId: string) => void;
}

export function DocumentList({
  documents,
  onDelete,
  onChatAbout,
  onOpenFigure,
}: DocumentListProps) {
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);
  const { figures, loading: loadingFigures, fetchFiguresForDoc } = useFigures();

  const handleToggleExpand = async (docId: string) => {
    if (expandedDocId === docId) {
      setExpandedDocId(null);
    } else {
      setExpandedDocId(docId);
      await fetchFiguresForDoc(docId);
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return '—';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch (e) {
      return dateString;
    }
  };

  return (
    <div className="w-full overflow-x-auto rounded-sm border border-neutral-border bg-surface shadow-sm">
      <table className="w-full min-w-[700px] border-collapse text-left text-xs font-semibold text-slate-300 font-sans">
        <thead className="bg-background text-slate-400 border-b border-neutral-border uppercase text-[9px] font-tech-mono tracking-widest">
          <tr>
            <th className="py-2.5 px-4 border-r border-neutral-border/20">Title / Filename</th>
            <th className="py-2.5 px-4 border-r border-neutral-border/20">Authors</th>
            <th className="py-2.5 px-4 border-r border-neutral-border/20 text-center">Pages</th>
            <th className="py-2.5 px-4 border-r border-neutral-border/20 text-center">Status</th>
            <th className="py-2.5 px-4 border-r border-neutral-border/20">Uploaded</th>
            <th className="py-2.5 px-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-border/40">
          {documents.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center py-10 text-slate-550 font-medium font-tech-mono uppercase tracking-wider text-[10px]">
                No research papers indexed. Use the uploader to begin.
              </td>
            </tr>
          ) : (
            documents.map((doc) => {
              const isExpanded = expandedDocId === doc.id;
              return (
                <React.Fragment key={doc.id}>
                  <tr className="hover:bg-background/30 transition-colors group">
                    <td className="py-3 px-4 max-w-xs md:max-w-sm border-r border-neutral-border/20">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleToggleExpand(doc.id)}
                          className="p-1 rounded-sm hover:bg-background text-slate-500 hover:text-slate-200 transition-colors border border-transparent hover:border-neutral-border/30"
                          title={isExpanded ? 'Collapse' : 'Expand extracted figures'}
                          disabled={doc.status !== 'ready'}
                        >
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>
                        <div className="flex flex-col truncate">
                          <span className="text-slate-100 font-editorial-serif text-sm font-bold truncate">
                            {doc.title || doc.filename}
                          </span>
                          {doc.title && (
                            <span className="text-[10px] text-slate-500 font-bold font-tech-mono mt-0.5 truncate">
                              {doc.filename}
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 max-w-[120px] truncate text-slate-400 font-medium border-r border-neutral-border/20">
                      {doc.authors && doc.authors.length > 0
                        ? doc.authors.join(', ')
                        : '—'}
                    </td>
                    <td className="py-3 px-4 text-center font-tech-mono font-bold text-slate-350 border-r border-neutral-border/20">
                      {doc.total_pages}
                    </td>
                    <td className="py-3 px-4 text-center border-r border-neutral-border/20">
                      <div className="flex items-center justify-center">
                        {doc.status === 'ready' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[9px] font-bold font-tech-mono bg-green-500/5 text-green-400 border border-green-500/20 uppercase tracking-wider">
                            Ready
                          </span>
                        )}
                        {doc.status === 'processing' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[9px] font-bold font-tech-mono bg-yellow-500/5 text-yellow-400 border border-yellow-500/20 uppercase tracking-wider">
                            Ingesting
                          </span>
                        )}
                        {doc.status === 'error' && (
                          <span
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[9px] font-bold font-tech-mono bg-red-500/5 text-red-400 border border-red-500/20 uppercase tracking-wider cursor-help"
                            title={doc.error_message || 'Pipeline error'}
                          >
                            Error
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-450 font-tech-mono text-[11px] border-r border-neutral-border/20">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {doc.status === 'ready' && (
                          <button
                            onClick={() => onChatAbout(doc.id)}
                            className="px-2 py-1 rounded-sm bg-background border border-neutral-border text-slate-300 hover:text-primary hover:border-primary/50 transition-all duration-150 text-[10px] font-bold font-tech-mono uppercase tracking-wider"
                          >
                            Chat
                          </button>
                        )}
                        <button
                          onClick={() => {
                            if (confirm(`Are you sure you want to delete '${doc.title || doc.filename}'? This will delete all chunks, embeddings, and extracted figures.`)) {
                              onDelete(doc.id);
                            }
                          }}
                          className="p-1 rounded-sm border border-neutral-border text-slate-500 hover:text-red-400 hover:border-red-500/20 hover:bg-red-500/5 transition-all duration-150"
                          title="Delete document"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                  {/* Expanded Figures Drawer */}
                  {isExpanded && (
                    <tr>
                      <td colSpan={6} className="bg-background/80 p-4 border-t border-neutral-border/40">
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-2 text-slate-400 font-bold text-[10px] uppercase font-tech-mono tracking-widest mb-2">
                            <ImageIcon className="w-3.5 h-3.5 text-primary" /> Extracted Figures & Diagrams
                          </div>
                          {loadingFigures ? (
                            <div className="flex items-center gap-2 text-slate-500 py-4 text-xs font-semibold font-tech-mono">
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" /> LOADING FIGURE THUMBNAILS...
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
                                  onClick={() => onOpenFigure(fig.image_url, fig.caption, fig.page_number, doc.id)}
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
  );
}
