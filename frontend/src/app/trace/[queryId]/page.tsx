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
    <div className="p-6 md:p-8 max-w-5xl mx-auto flex flex-col gap-6">
      <div className="flex items-center">
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-1 text-xs font-bold text-slate-400 hover:text-indigo-400 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Conversation
        </button>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-24 select-none">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-400 mb-3" />
          <p className="text-xs font-bold text-slate-400 animate-pulse uppercase tracking-wider">
            Fetching agent execution path...
          </p>
        </div>
      )}

      {!loading && error && (
        <div className="p-5 rounded-2xl border border-red-500/20 bg-red-500/5 text-red-400 text-xs font-semibold flex flex-col gap-3 max-w-xl mx-auto text-center items-center justify-center mt-12">
          <AlertCircle className="w-8 h-8 text-red-500" />
          <div>
            <h3 className="font-extrabold text-sm text-slate-200">Failed to Retrieve Trace</h3>
            <p className="mt-1 text-slate-400 leading-relaxed">{error}</p>
          </div>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-350 text-xs font-bold rounded-lg transition-colors border border-slate-700/50 mt-2"
          >
            Go Back
          </button>
        </div>
      )}

      {!loading && !error && trace && (
        <TraceTimeline trace={trace} />
      )}
    </div>
  );
}
