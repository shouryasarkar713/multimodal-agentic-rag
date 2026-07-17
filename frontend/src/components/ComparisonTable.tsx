import React from 'react';
import { FileText, Compare, AlertCircle, HelpCircle } from 'lucide-react';
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
      <div className="w-full flex flex-col gap-6 font-sans">
        {/* Side-by-Side Metadata Headers (Skeleton) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-sm border border-dashed border-neutral-border/30 bg-surface/30 flex flex-col gap-2 min-h-[100px] justify-center items-center text-center">
            <span className="text-[9px] uppercase font-bold text-slate-500 font-tech-mono tracking-widest">
              Paper A Context
            </span>
            <p className="text-[10px] text-slate-600 font-tech-mono italic">
              [ Awaiting Paper A Selection ]
            </p>
          </div>

          <div className="p-4 rounded-sm border border-dashed border-neutral-border/30 bg-surface/30 flex flex-col gap-2 min-h-[100px] justify-center items-center text-center">
            <span className="text-[9px] uppercase font-bold text-slate-500 font-tech-mono tracking-widest">
              Paper B Context
            </span>
            <p className="text-[10px] text-slate-600 font-tech-mono italic">
              [ Awaiting Paper B Selection ]
            </p>
          </div>
        </div>

        {/* Side-by-Side Extracted Evidence Panel (Skeleton columns) */}
        <div className="flex flex-col gap-3">
          <span className="text-[9px] uppercase font-bold text-slate-600 font-tech-mono tracking-widest pl-1">
            Comparative Evidence Columns
          </span>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 min-h-[300px]">
            <div className="border border-neutral-border/20 bg-surface/10 rounded-sm p-6 flex flex-col items-center justify-center text-center">
              <span className="text-[10px] text-slate-600 font-tech-mono uppercase tracking-wider">
                Evidence Left Rail
              </span>
              <p className="text-[9px] text-slate-700 font-tech-mono mt-1">
                Select documents & query to stream citations.
              </p>
            </div>
            
            <div className="border border-neutral-border/20 bg-surface/10 rounded-sm p-6 flex flex-col items-center justify-center text-center">
              <span className="text-[10px] text-slate-600 font-tech-mono uppercase tracking-wider">
                Evidence Right Rail
              </span>
              <p className="text-[9px] text-slate-700 font-tech-mono mt-1">
                Select documents & query to stream citations.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Filter chunks by document ID
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
    <div className="w-full flex flex-col gap-6 font-sans">
      {/* Side-by-Side Metadata Headers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Paper A Header */}
        <div className="p-4 rounded-sm scholarly-panel flex items-start gap-3">
          <FileText className="w-5 h-5 text-primary shrink-0 mt-0.5" />
          <div className="min-w-0">
            <span className="text-[9px] uppercase font-bold text-primary font-tech-mono tracking-widest">PAPER A / LEFT CONTEXT</span>
            <h4 className="font-bold text-sm text-slate-200 font-editorial-serif truncate mt-0.5">{paperA.title || paperA.filename}</h4>
            <p className="text-[10px] text-slate-500 font-grotesk-sans truncate mt-0.5">{paperA.authors?.join(', ') || 'Unknown Authors'}</p>
          </div>
        </div>

        {/* Paper B Header */}
        <div className="p-4 rounded-sm scholarly-panel flex items-start gap-3">
          <FileText className="w-5 h-5 text-primary shrink-0 mt-0.5" />
          <div className="min-w-0">
            <span className="text-[9px] uppercase font-bold text-primary font-tech-mono tracking-widest">PAPER B / RIGHT CONTEXT</span>
            <h4 className="font-bold text-sm text-slate-200 font-editorial-serif truncate mt-0.5">{paperB.title || paperB.filename}</h4>
            <p className="text-[10px] text-slate-500 font-grotesk-sans truncate mt-0.5">{paperB.authors?.join(', ') || 'Unknown Authors'}</p>
          </div>
        </div>
      </div>

      {/* comparative answer summary panel */}
      {comparativeAnswer && (
        <div className="p-5 rounded-sm border border-neutral-border bg-surface shadow-sm flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-neutral-border/30 pb-2">
            <span className="text-[9px] uppercase font-bold text-primary font-tech-mono tracking-widest">Unified Comparative Analysis</span>
          </div>
          <div className="text-xs md:text-sm font-medium text-slate-250 font-editorial-serif leading-relaxed whitespace-pre-wrap">
            {comparativeAnswer}
          </div>
        </div>
      )}

      {/* decomposed multi-hop sub-queries list */}
      {subQueries.length > 0 && (
        <div className="p-4 rounded-sm border border-neutral-border bg-background/30">
          <span className="text-[9px] uppercase font-bold text-slate-550 font-tech-mono tracking-widest block mb-2">Decomposed Sub-Queries</span>
          <ul className="flex flex-col gap-1.5 list-disc list-inside text-xs text-slate-400 font-medium font-grotesk-sans">
            {subQueries.map((sq, i) => (
              <li key={i}>{sq}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Side-by-Side Extracted Evidence Panel */}
      {subResults.length > 0 && (
        <div className="flex flex-col gap-3">
          <span className="text-[9px] uppercase font-bold text-slate-500 font-tech-mono tracking-widest pl-1">Extracted Source Evidence</span>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Chunks for Paper A */}
            <div className="flex flex-col gap-3">
              {chunksA.length === 0 ? (
                <div className="text-center p-6 border border-neutral-border/30 bg-surface rounded-sm text-slate-550 text-xs italic font-medium font-tech-mono uppercase tracking-wide">
                  No text evidence retrieved for Paper A.
                </div>
              ) : (
                chunksA.map((c, i) => (
                  <div key={c.id} className="p-4 rounded-sm border border-neutral-border bg-surface/50 flex flex-col gap-2">
                    <div className="flex items-center justify-between border-b border-neutral-border/20 pb-1.5 font-tech-mono text-[9px] text-slate-500 font-bold">
                      <span>Evidence {i+1}</span>
                      <span className="bg-background border border-neutral-border/30 px-1 rounded-sm">PAGE {c.page_number}</span>
                    </div>
                    {c.section_title && (
                      <div className="text-[9px] text-primary/80 font-tech-mono uppercase tracking-wide">Sec: {c.section_title}</div>
                    )}
                    <p className="text-xs text-slate-400 font-grotesk-sans font-medium leading-relaxed italic">
                      "{c.content_markdown || c.content_text}"
                    </p>
                  </div>
                ))
              )}
            </div>

            {/* Chunks for Paper B */}
            <div className="flex flex-col gap-3">
              {chunksB.length === 0 ? (
                <div className="text-center p-6 border border-neutral-border/30 bg-surface rounded-sm text-slate-550 text-xs italic font-medium font-tech-mono uppercase tracking-wide">
                  No text evidence retrieved for Paper B.
                </div>
              ) : (
                chunksB.map((c, i) => (
                  <div key={c.id} className="p-4 rounded-sm border border-neutral-border bg-surface/50 flex flex-col gap-2">
                    <div className="flex items-center justify-between border-b border-neutral-border/20 pb-1.5 font-tech-mono text-[9px] text-slate-500 font-bold">
                      <span>Evidence {i+1}</span>
                      <span className="bg-background border border-neutral-border/30 px-1 rounded-sm">PAGE {c.page_number}</span>
                    </div>
                    {c.section_title && (
                      <div className="text-[9px] text-primary/80 font-tech-mono uppercase tracking-wide">Sec: {c.section_title}</div>
                    )}
                    <p className="text-xs text-slate-400 font-grotesk-sans font-medium leading-relaxed italic">
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
