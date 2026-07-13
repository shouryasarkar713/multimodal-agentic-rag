'use client';

import React, { useState } from 'react';
import { Columns, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import { useDocuments } from '../../hooks/useDocuments';
import { api } from '../../lib/api';
import { Citation } from '../../lib/types';
import { ComparisonTable } from '../../components/ComparisonTable';

export default function ComparePage() {
  const { documents } = useDocuments();
  const [docAId, setDocAId] = useState<string>('');
  const [docBId, setDocBId] = useState<string>('');
  const [query, setQuery] = useState('');
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [subQueries, setSubQueries] = useState<string[]>([]);
  const [subResults, setSubResults] = useState<any[]>([]);
  const [comparativeAnswer, setComparativeAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);

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
      const session = await api.createSession(`Comparison: ${paperA?.filename.slice(0, 10)} vs ${paperB?.filename.slice(0, 10)}`);
      
      const fullQuery = `Compare: ${query}`;
      const res = await api.chat({
        session_id: session.id,
        query: fullQuery,
        document_ids: [docAId, docBId],
      });

      const trace = await api.getTrace(res.trace_id);
      
      const hopStep = trace.steps.find((s) => s.step_name === 'multi_hop_decomposition');
      if (hopStep && hopStep.metadata) {
        setSubQueries(hopStep.metadata.sub_queries || []);
        const results = hopStep.metadata.sub_queries.map((q: string, idx: number) => {
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
    <div className="p-6 md:p-8 max-w-7xl mx-auto flex flex-col gap-8">
      <div>
        <div className="flex items-center gap-2">
          <Columns className="w-5 h-5 text-indigo-400" />
          <h1 className="font-extrabold text-2xl text-slate-100 tracking-tight">
            Side-by-Side Comparison Workspace
          </h1>
        </div>
        <p className="text-xs text-slate-400 mt-1 font-semibold">
          Select two papers, query comparative variables, and inspect results section-by-section.
        </p>
      </div>

      <form onSubmit={handleCompareSubmit} className="p-5 rounded-2xl border border-slate-800 bg-slate-900/40 flex flex-col gap-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Select Paper A</label>
            <select
              value={docAId}
              onChange={(e) => setDocAId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-semibold text-slate-200 focus:outline-none focus:border-indigo-500/80 cursor-pointer"
            >
              <option value="">-- Choose Paper A --</option>
              {readyDocuments.map((doc) => (
                <option key={doc.id} value={doc.id} disabled={doc.id === docBId}>
                  {doc.title || doc.filename}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Select Paper B</label>
            <select
              value={docBId}
              onChange={(e) => setDocBId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-semibold text-slate-200 focus:outline-none focus:border-indigo-500/80 cursor-pointer"
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

        <div className="flex flex-col gap-1.5">
          <label className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Comparison Topic / Question</label>
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Compare the training architectures, baseline dataset splits, or benchmark accuracy."
              className="flex-1 px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-semibold text-slate-200 placeholder-slate-650 focus:outline-none focus:border-indigo-500/80"
              disabled={comparing}
            />
            <button
              type="submit"
              disabled={comparing || !docAId || !docBId || !query.trim()}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white disabled:text-slate-600 text-xs font-extrabold rounded-xl transition-all duration-150 shadow-lg shadow-indigo-650/20 disabled:shadow-none flex items-center gap-1.5"
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

        {error && (
          <div className="flex items-center gap-2 p-3 border border-red-500/20 bg-red-500/5 text-red-400 text-xs font-semibold rounded-lg">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </form>

      {comparing ? (
        <div className="flex flex-col items-center justify-center p-16 select-none">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-400 mb-3" />
          <p className="text-xs font-bold text-slate-400 animate-pulse uppercase tracking-wider">
            Decomposing and running multi-hop agent retrieval...
          </p>
        </div>
      ) : (
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
      )}
    </div>
  );
}
