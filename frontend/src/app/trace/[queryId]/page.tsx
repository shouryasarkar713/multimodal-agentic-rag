'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import { api } from '../../../lib/api';
import { QueryTrace } from '../../../lib/types';
import { TraceTimeline } from '../../../components/TraceTimeline';

export default function TracePage() {
  const params = useParams();
  const router = useRouter();
  const queryId = params?.queryId as string;

  const [trace, setTrace] = useState<QueryTrace | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!queryId) return;

    const fetchTrace = async () => {
      try {
        setLoading(true);
        const data = await api.getTrace(queryId);
        setTrace(data);
      } catch (err: any) {
        setError(err.message || 'Failed to retrieve query execution trace.');
      } finally {
        setLoading(false);
      }
    };

    fetchTrace();
  }, [queryId]);

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto flex flex-col gap-6 font-sans">
      {/* Back Button */}
      <div className="flex items-center">
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-sm bg-background border border-neutral-border hover:border-primary/50 text-slate-400 hover:text-primary font-bold font-tech-mono text-[10px] uppercase tracking-wider transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 text-primary" /> Back to Conversation
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-24 select-none">
          <Loader2 className="w-8 h-8 animate-spin text-primary mb-3" />
          <p className="text-xs font-bold text-slate-500 font-tech-mono uppercase tracking-widest animate-pulse">
            Fetching agent execution path...
          </p>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="p-6 rounded-sm border border-neutral-border bg-surface text-slate-400 text-xs font-semibold flex flex-col gap-3 max-w-xl mx-auto text-center items-center justify-center mt-12">
          <AlertCircle className="w-8 h-8 text-red-500" />
          <div>
            <h3 className="font-bold text-sm text-slate-200 font-editorial-serif">Failed to Retrieve Trace</h3>
            <p className="mt-1 text-slate-500 leading-relaxed font-grotesk-sans">{error}</p>
          </div>
          <button
            onClick={() => router.back()}
            className="px-4 py-1.5 rounded-sm bg-background border border-neutral-border text-xs font-bold font-tech-mono uppercase tracking-wider text-slate-355 hover:text-primary hover:border-primary/50 transition-colors mt-2"
          >
            Go Back
          </button>
        </div>
      )}

      {/* Trace Timeline Display */}
      {!loading && !error && trace && (
        <TraceTimeline trace={trace} />
      )}
    </div>
  );
}
