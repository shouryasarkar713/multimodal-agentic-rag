import React, { useState } from 'react';
import { FileText, Trash2, Image as ImageIcon, CheckCircle2, Loader2, XCircle, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { Document } from '../lib/types';
import { api } from '../lib/api';

interface DocumentListProps {
  documents: Document[];
  onDelete: (id: string) => Promise<void>;
  onChatAbout: (docId: string) => void;
  onOpenFigure: (imagePath: string, caption: string, pageNumber: number, documentId: string) => void;
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
      console.error('Failed to load figures', err);
      setFigures([]);
    } finally {
      setLoadingFigures(false);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className="w-full overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/50">
      <table className="w-full min-w-[700px] border-collapse text-left text-xs font-semibold text-slate-300">
        <thead className="bg-slate-800/40 text-slate-400 border-b border-slate-800 uppercase text-[10px] tracking-wider">
          <tr>
            <th className="py-3 px-4">Title / Filename</th>
            <th className="py-3 px-4">Authors</th>
            <th className="py-3 px-4 text-center">Pages</th>
            <th className="py-3 px-4 text-center">Status</th>
            <th className="py-3 px-4">Uploaded</th>
            <th className="py-3 px-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {documents.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center py-12 text-slate-500 font-medium">
                No research papers ingested yet. Use the uploader above to begin.
              </td>
            </tr>
          ) : (
            documents.map((doc) => {
              const isExpanded = expandedDocId === doc.id;
              return (
                <React.Fragment key={doc.id}>
                  <tr className="hover:bg-slate-800/20 transition-colors group">
                    <td className="py-4 px-4 max-w-xs md:max-w-sm">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handleToggleExpand(doc.id)}
                          className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-200 transition-colors"
                          title={isExpanded ? 'Collapse' : 'Expand extracted figures'}
                          disabled={doc.status !== 'ready'}
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                        <div className="flex flex-col truncate">
                          <span className="text-slate-100 font-bold truncate">
                            {doc.title || doc.filename}
                          </span>
                          {doc.title && (
                            <span className="text-[10px] text-slate-500 font-medium font-mono mt-0.5 truncate">
                              {doc.filename}
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4 max-w-[120px] truncate text-slate-400 font-medium">
                      {doc.authors && doc.authors.length > 0
                        ? doc.authors.join(', ')
                        : '—'}
                    </td>
                    <td className="py-4 px-4 text-center font-mono font-bold text-slate-300">
                      {doc.total_pages}
                    </td>
                    <td className="py-4 px-4 text-center">
                      <div className="flex items-center justify-center">
                        {doc.status === 'ready' && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-green-500/10 text-green-400 border border-green-500/20">
                            <CheckCircle2 className="w-3 h-3" /> Ready
                          </span>
                        )}
                        {doc.status === 'processing' && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 animate-pulse">
                            <Loader2 className="w-3 h-3 animate-spin" /> Ingesting
                          </span>
                        )}
                        {doc.status === 'error' && (
                          <span
                            className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20 cursor-help"
                            title={doc.error_message || 'Pipeline error'}
                          >
                            <XCircle className="w-3 h-3" /> Error
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-4 text-slate-400 font-medium">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {doc.status === 'ready' && (
                          <button
                            onClick={() => onChatAbout(doc.id)}
                            className="px-2.5 py-1 rounded bg-indigo-600/10 text-indigo-400 border border-indigo-500/25 hover:bg-indigo-600 hover:text-white transition-all duration-150 text-[10px] font-bold"
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
                          className="p-1.5 rounded border border-slate-800 text-slate-500 hover:text-red-400 hover:border-red-500/30 hover:bg-red-500/5 transition-all duration-150 opacity-0 group-hover:opacity-100"
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
                      <td colSpan={6} className="bg-slate-900/60 p-4 border-t border-slate-800/30">
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-2 text-slate-400 font-bold text-[10px] uppercase tracking-wider mb-2">
                            <ImageIcon className="w-3.5 h-3.5 text-indigo-400" /> Extracted Figures & Diagrams
                          </div>
                          {loadingFigures ? (
                            <div className="flex items-center gap-2 text-slate-500 py-4 text-xs font-semibold">
                              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" /> Loading figure thumbnails...
                            </div>
                          ) : figures.length === 0 ? (
                            <div className="text-slate-600 text-xs py-4 font-medium italic">
                              No figures extracted from this document.
                            </div>
                          ) : (
                            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
                              {figures.map((fig) => (
                                <div
                                  key={fig.chunk_id}
                                  className="relative aspect-video rounded-lg border border-slate-800 bg-slate-950 overflow-hidden cursor-pointer hover:border-indigo-500/50 hover:shadow-lg transition-all duration-200 group/fig"
                                  onClick={() => onOpenFigure(fig.image_url, fig.caption, fig.page_number, doc.id)}
                                >
                                  {/* Thumbnail */}
                                  <img
                                    src={`${process.env.NEXT_PUBLIC_API_URL ? process.env.NEXT_PUBLIC_API_URL.replace('/api', '') : 'http://localhost:8000'}${fig.image_url}`}
                                    alt={fig.caption || 'Extracted Figure'}
                                    className="w-full h-full object-cover group-hover/fig:scale-[1.03] transition-transform duration-200"
                                  />
                                  <div className="absolute bottom-0 inset-x-0 bg-slate-950/80 p-1.5 border-t border-slate-800/40 text-[9px] text-slate-400 truncate font-semibold">
                                    Page {fig.page_number}: {fig.caption || 'No caption'}
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
