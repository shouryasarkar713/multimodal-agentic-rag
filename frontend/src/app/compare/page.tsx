'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Columns, Loader2, Sparkles, AlertCircle, MessageSquare, ArrowRight } from 'lucide-react';
import { useDocuments } from '../../hooks/useDocuments';
import { api } from '../../lib/api';
import { Citation } from '../../lib/types';
import { ComparisonTable } from '../../components/ComparisonTable';

export default function ComparePage() {
  const router = useRouter();
  const { documents } = useDocuments();
  const [docAId, setDocAId] = useState<string>('');
  const [docBId, setDocBId] = useState<string>('');
  const [query, setQuery] = useState('');
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Comparison execution states
  const [subQueries, setSubQueries] = useState<string[]>([]);
  const [subResults, setSubResults] = useState<any[]>([]);
  const [comparativeAnswer, setComparativeAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [lastSessionId, setLastSessionId] = useState<string | null>(null);

  const readyDocuments = documents.filter((d) => d.status === 'ready');
  const paperA = readyDocuments.find((d) => d.id === docAId) || null;
  const paperB = readyDocuments.find((d) => d.id === docBId) || null;

  const handleCompareSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docAId || !docBId) {
      setError('Please select both Paper A and Paper B.');
      return;
    }
    if (!query.trim()) {
      setError('Please enter a comparison topic or question.');
      return;
    }

    setComparing(true);
    setError(null);
    setSubQueries([]);
    setSubResults([]);
    setComparativeAnswer(null);
    setCitations([]);

    try {
      // 1. Create a temporary chat session for this comparison
      const session = await api.createSession(`Comparison: ${paperA?.filename.slice(0, 10)} vs ${paperB?.filename.slice(0, 10)}`);

      // Save document scope to localStorage for this session so it persists when navigating to chat
      if (typeof window !== 'undefined') {
        localStorage.setItem(`session_docs_${session.id}`, JSON.stringify([docAId, docBId]));
      }
      setLastSessionId(session.id);
      // Prefix with comparative instruction to guide classifier intent
      const fullQuery = `Compare: ${query}`;
      const res = await api.chat({
        session_id: session.id,
        query: fullQuery,
        document_ids: [docAId, docBId],
      });

      // 3. Since the comparison runs inside the multi-hop LangGraph graph path,
      // let's fetch the trace if we need raw sub-results, or parse the citations & answer.
      // Fetch detailed execution traces to render sub-queries and sub-results
      const trace = await api.getTrace(res.trace_id);
      
      // Find multi-hop node step in trace
      const hopStep = trace.steps.find((s) => s.step_name === 'multi_hop_decomposition');
      if (hopStep && hopStep.metadata) {
        setSubQueries(hopStep.metadata.sub_queries || []);
        // Chunks categorized by sub-query
        const results = hopStep.metadata.sub_queries.map((q: string, idx: number) => {
          // Flatten chunks from citations matching Paper A or B
          return {
            sub_query: q,
            retrieved_chunks: res.citations.map((c: any) => ({
              id: c.chunk_id,
              document_id: c.document_id,
              page_number: c.page_number,
              section_title: c.section_title,
              content_text: c.excerpt,
              content_markdown: c.excerpt,
            })),
          };
        });
        setSubResults(results);
      } else {
        // Fallback sub-results grouping
        const mockResults = [
          {
            sub_query: `Analysis of ${paperA?.title || paperA?.filename}`,
            retrieved_chunks: res.citations.filter((c: any) => c.document_id === docAId).map((c: any) => ({
              id: c.chunk_id,
              document_id: c.document_id,
              page_number: c.page_number,
              section_title: c.section_title,
              content_text: c.excerpt,
              content_markdown: c.excerpt,
            })),
          },
          {
            sub_query: `Analysis of ${paperB?.title || paperB?.filename}`,
            retrieved_chunks: res.citations.filter((c: any) => c.document_id === docBId).map((c: any) => ({
              id: c.chunk_id,
              document_id: c.document_id,
              page_number: c.page_number,
              section_title: c.section_title,
              content_text: c.excerpt,
              content_markdown: c.excerpt,
            })),
          },
        ];
        setSubResults(mockResults);
      }

      setComparativeAnswer(res.content);
      setCitations(res.citations);
      
    } catch (err: any) {
      setError(err.message || 'Comparison failed. Check backend connection.');
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto flex flex-col gap-8 font-sans">
      {/* Header */}
      <div className="border-b border-neutral-border pb-4">
        <div className="flex items-center gap-2">
          <Columns className="w-5 h-5 text-primary" />
          <h1 className="font-bold text-2xl text-slate-100 font-editorial-serif tracking-tight">
            Side-by-Side Comparison Workspace
          </h1>
        </div>
        <p className="text-xs text-slate-455 mt-1 font-tech-mono uppercase tracking-wide">
          /cross_paper_variable_analysis
        </p>
      </div>

      {/* Comparison Controller Form */}
      <form onSubmit={handleCompareSubmit} className="p-5 rounded-sm border border-neutral-border bg-surface flex flex-col gap-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Dropdown Paper A */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[9px] uppercase font-bold text-slate-500 font-tech-mono tracking-widest">Select Paper A</label>
            <select
              value={docAId}
              onChange={(e) => setDocAId(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-neutral-border rounded-sm text-xs font-semibold text-slate-200 focus:outline-none focus:border-primary cursor-pointer font-tech-mono"
            >
              <option value="">-- Choose Paper A --</option>
              {readyDocuments.map((doc) => (
                <option key={doc.id} value={doc.id} disabled={doc.id === docBId}>
                  {doc.title || doc.filename}
                </option>
              ))}
            </select>
          </div>

          {/* Dropdown Paper B */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[9px] uppercase font-bold text-slate-500 font-tech-mono tracking-widest">Select Paper B</label>
            <select
              value={docBId}
              onChange={(e) => setDocBId(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-neutral-border rounded-sm text-xs font-semibold text-slate-200 focus:outline-none focus:border-primary cursor-pointer font-tech-mono"
            >
              <option value="">-- Choose Paper B --</option>
              {readyDocuments.map((doc) => (
                <option key={doc.id} value={doc.id} disabled={doc.id === docAId}>
                  {doc.title || doc.filename}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Comparison Query Prompt Input */}
        <div className="flex flex-col gap-1.5">
          <label className="text-[9px] uppercase font-bold text-slate-500 font-tech-mono tracking-widest">Comparison Topic / Question</label>
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Compare the training architectures, baseline dataset splits, or benchmark accuracy."
              className="flex-1 px-4 py-2.5 bg-background border border-neutral-border rounded-sm text-xs font-semibold text-slate-200 placeholder-slate-650 focus:outline-none focus:border-primary font-tech-mono"
              disabled={comparing}
            />
            <button
              type="submit"
              disabled={comparing || !docAId || !docBId || !query.trim()}
              className="px-5 py-2.5 bg-background border border-neutral-border hover:border-primary/50 text-slate-200 hover:text-primary disabled:text-slate-770 disabled:border-neutral-border/20 text-xs font-bold font-tech-mono uppercase tracking-wider rounded-sm transition-all duration-150 flex items-center gap-1.5"
            >
              {comparing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Comparing
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" /> Analyze
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-2 p-3 border border-red-500/20 bg-red-500/5 text-red-400 text-xs font-bold rounded-sm font-tech-mono uppercase tracking-wider">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </form>

      {/* Comparison Grid Results */}
      {comparing ? (
        <div className="flex flex-col items-center justify-center p-16 select-none">
          <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
          <p className="text-xs font-bold text-slate-500 animate-pulse uppercase tracking-widest font-tech-mono">
            Decomposing and running multi-hop agent retrieval...
          </p>
        </div>
      ) : (
        <>
          <ComparisonTable
            paperA={paperA}
            paperB={paperB}
            comparisonQuery={query}
            isComparing={comparing}
            subQueries={subQueries}
            subResults={subResults}
            comparativeAnswer={comparativeAnswer}
            citations={citations}
          />
          {/* Continue in Chat Button */}
          {lastSessionId && comparativeAnswer && (
            <div className="p-4 rounded-sm border border-neutral-border bg-surface flex items-center justify-between font-sans">
              <div>
                <p className="text-xs font-bold text-primary font-tech-mono uppercase tracking-wider">Comparison Complete</p>
                <p className="text-[10px] text-slate-550 mt-0.5 font-grotesk-sans">Continue the conversation with both papers in scope</p>
              </div>
              <button
                onClick={() => router.push(`/chat?session=${lastSessionId}`)}
                className="px-4 py-2 bg-background border border-neutral-border hover:border-primary/50 text-slate-200 hover:text-primary text-xs font-bold font-tech-mono uppercase tracking-wider rounded-sm transition-colors flex items-center gap-1.5"
              >
                <MessageSquare className="w-3.5 h-3.5 text-primary" />
                <ArrowRight className="w-3.5 h-3.5 text-primary" />
                <span>Continue in Chat</span>
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
