import React from 'react';
import { FileText, HelpCircle } from 'lucide-react';
import { Document, Citation } from '../lib/types';

interface ComparisonTableProps {
  paperA: Document | null;
  paperB: Document | null;
  comparisonQuery: string;
  isComparing: boolean;
  subQueries: string[];
  subResults: { sub_query: string; retrieved_chunks: any[] }[];
  comparativeAnswer: string | null;
  citations: Citation[];
}

export function ComparisonTable({
  paperA,
  paperB,
  comparisonQuery,
  isComparing,
  subQueries,
  subResults,
  comparativeAnswer,
  citations,
}: ComparisonTableProps) {
  if (!paperA || !paperB) {
    return (
      <div className="flex flex-col items-center justify-center p-12 border border-slate-800 rounded-2xl bg-slate-900/20 text-slate-500 font-semibold select-none text-center">
        <HelpCircle className="w-10 h-10 mb-3 text-slate-600" />
        <p className="text-xs">Select two documents from the dropdowns above to open the comparison workspace.</p>
      </div>
    );
  }

  const getChunksForDoc = (docId: string, resultsList: typeof subResults) => {
    const list: any[] = [];
    const seenIds = new Set<string>();

    for (const res of resultsList) {
      for (const chunk of res.retrieved_chunks) {
        if (chunk.document_id === docId && !seenIds.has(chunk.id)) {
          seenIds.add(chunk.id);
          list.push(chunk);
        }
      }
    }
    return list;
  };

  const chunksA = getChunksForDoc(paperA.id, subResults);
  const chunksB = getChunksForDoc(paperB.id, subResults);

  return (
    <div className="w-full flex flex-col gap-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-950/10 flex items-start gap-3">
          <FileText className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
          <div className="min-w-0">
            <span className="text-[9px] uppercase font-bold text-indigo-400 tracking-wider">PAPER A (Left Panel)</span>
            <h4 className="font-extrabold text-sm text-slate-200 truncate mt-0.5">{paperA.title || paperA.filename}</h4>
            <p className="text-[10px] text-slate-500 font-medium truncate mt-0.5">{paperA.authors?.join(', ') || 'Unknown Authors'}</p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-violet-500/20 bg-violet-950/10 flex items-start gap-3">
          <FileText className="w-5 h-5 text-violet-400 shrink-0 mt-0.5" />
          <div className="min-w-0">
            <span className="text-[9px] uppercase font-bold text-violet-400 tracking-wider">PAPER B (Right Panel)</span>
            <h4 className="font-extrabold text-sm text-slate-200 truncate mt-0.5">{paperB.title || paperB.filename}</h4>
            <p className="text-[10px] text-slate-500 font-medium truncate mt-0.5">{paperB.authors?.join(', ') || 'Unknown Authors'}</p>
          </div>
        </div>
      </div>

      {comparativeAnswer && (
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900 shadow-xl flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-slate-850 pb-2.5">
            <span className="text-[10px] uppercase font-bold text-indigo-400 tracking-wider">Unified Comparative Analysis</span>
          </div>
          <div className="text-xs md:text-sm font-semibold text-slate-200 leading-relaxed whitespace-pre-wrap">
            {comparativeAnswer}
          </div>
        </div>
      )}

      {subQueries.length > 0 && (
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30">
          <span className="text-[9px] uppercase font-extrabold text-slate-500 tracking-wider block mb-2">Decomposed Sub-Queries</span>
          <ul className="flex flex-col gap-1.5 list-disc list-inside text-xs text-slate-400 font-medium">
            {subQueries.map((sq, i) => (
              <li key={i}>{sq}</li>
            ))}
          </ul>
        </div>
      )}

      {subResults.length > 0 && (
        <div className="flex flex-col gap-3">
          <span className="text-[10px] uppercase font-extrabold text-slate-500 tracking-wider pl-1">Extracted Source Evidence</span>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-3">
              {chunksA.length === 0 ? (
                <div className="text-center p-6 border border-slate-850 rounded-xl text-slate-600 text-xs italic font-medium">
                  No text evidence retrieved for Paper A.
                </div>
              ) : (
                chunksA.map((c, i) => (
                  <div key={c.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/30 flex flex-col gap-2">
                    <div className="flex items-center justify-between border-b border-slate-850 pb-1.5">
                      <span className="text-[9px] font-mono text-slate-500 font-bold">Evidence {i+1}</span>
                      <span className="text-[9px] font-mono text-slate-500 bg-slate-900 px-1 rounded">Page {c.page_number}</span>
                    </div>
                    {c.section_title && (
                      <div className="text-[9px] text-indigo-400/80 font-bold">Section: {c.section_title}</div>
                    )}
                    <p className="text-xs text-slate-400 font-medium leading-relaxed italic">
                      "{c.content_markdown || c.content_text}"
                    </p>
                  </div>
                ))
              )}
            </div>

            <div className="flex flex-col gap-3">
              {chunksB.length === 0 ? (
                <div className="text-center p-6 border border-slate-850 rounded-xl text-slate-600 text-xs italic font-medium">
                  No text evidence retrieved for Paper B.
                </div>
              ) : (
                chunksB.map((c, i) => (
                  <div key={c.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/30 flex flex-col gap-2">
                    <div className="flex items-center justify-between border-b border-slate-850 pb-1.5">
                      <span className="text-[9px] font-mono text-slate-500 font-bold">Evidence {i+1}</span>
                      <span className="text-[9px] font-mono text-slate-500 bg-slate-900 px-1 rounded">Page {c.page_number}</span>
                    </div>
                    {c.section_title && (
                      <div className="text-[9px] text-violet-400/80 font-bold">Section: {c.section_title}</div>
                    )}
                    <p className="text-xs text-slate-400 font-medium leading-relaxed italic">
                      "{c.content_markdown || c.content_text}"
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
