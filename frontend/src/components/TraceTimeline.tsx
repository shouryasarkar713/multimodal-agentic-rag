import React, { useState } from 'react';
import { Activity, Clock, Layers, ChevronDown, ChevronUp, Link as LinkIcon, Database } from 'lucide-react';
import { QueryTrace, TraceStep } from '../lib/types';

interface TraceTimelineProps {
  trace: QueryTrace;
}

export function TraceTimeline({ trace }: TraceTimelineProps) {
  return (
    <div className="w-full flex flex-col gap-6">
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl flex flex-col gap-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-md">
              <Activity className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h2 className="font-extrabold text-base text-slate-100">
                Agent Query Execution Trace
              </h2>
              <p className="text-[10px] font-mono text-slate-500 mt-0.5">
                ID: {trace.id}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800/80">
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-[10px] text-slate-400 font-semibold uppercase">Duration:</span>
              <span className="text-xs font-mono font-bold text-slate-200">{trace.total_duration_ms} ms</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-950/40 border border-indigo-900/50">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-[10px] text-slate-400 font-semibold uppercase">Intent:</span>
              <span className="text-xs font-bold text-indigo-400 uppercase">{trace.classified_intent || 'paper_qa'}</span>
            </div>
          </div>
        </div>

        <div className="bg-slate-950/40 border border-slate-800 p-4 rounded-xl">
          <div className="text-[10px] uppercase font-bold text-indigo-400 tracking-wider mb-1.5">
            Trigger Query
          </div>
          <p className="text-xs md:text-sm font-semibold text-slate-200 italic">
            "{trace.user_query}"
          </p>
        </div>

        {trace.langsmith_url && (
          <div className="flex items-center">
            <a
              href={trace.langsmith_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-600/10 text-indigo-400 hover:bg-indigo-600 hover:text-white border border-indigo-500/25 transition-all text-xs font-bold"
            >
              <LinkIcon className="w-3.5 h-3.5" /> View Trace in LangSmith (External)
            </a>
          </div>
        )}
      </div>

      <div className="flex flex-col relative pl-4 sm:pl-8 before:absolute before:left-8 before:top-4 before:bottom-4 before:w-0.5 before:bg-slate-800/80 before:z-0">
        <h3 className="text-xs uppercase font-extrabold tracking-wider text-slate-500 mb-6 pl-4 select-none">
          Execution Node Flow
        </h3>
        
        {trace.steps.map((step, idx) => (
          <TimelineStepNode key={idx} step={step} index={idx} isLast={idx === trace.steps.length - 1} />
        ))}
      </div>
    </div>
  );
}

interface TimelineStepNodeProps {
  step: TraceStep;
  index: number;
  isLast: boolean;
}

function TimelineStepNode({ step, index, isLast }: TimelineStepNodeProps) {
  const [isOpen, setIsOpen] = useState(false);

  const getStepTitle = (name: string) => {
    return name
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getStepColorClass = (name: string) => {
    switch (name) {
      case 'query_understanding':
        return 'bg-blue-500 border-blue-400 text-blue-400';
      case 'retrieval_orchestrator':
      case 'multi_hop_decomposition':
        return 'bg-violet-500 border-violet-400 text-violet-400';
      case 'evidence_grader':
      case 'query_rewriter':
        return 'bg-amber-500 border-amber-400 text-amber-400';
      case 'generator':
        return 'bg-green-500 border-green-400 text-green-400';
      case 'hallucination_validator':
        return 'bg-red-500 border-red-400 text-red-400';
      default:
        return 'bg-indigo-500 border-indigo-400 text-indigo-400';
    }
  };

  return (
    <div className="relative pb-8 pl-8 group">
      <div className={`absolute left-[-26px] top-1 w-5 h-5 rounded-full border-4 border-slate-900 flex items-center justify-center z-10 shadow-lg ${getStepColorClass(step.step_name).split(' ')[0]}`} />

      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 hover:bg-slate-900/60 hover:border-slate-700/50 shadow-sm transition-all duration-200 flex flex-col gap-2.5">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-slate-500 font-bold">
              0{index + 1}
            </span>
            <h4 className="font-extrabold text-sm text-slate-200">
              {getStepTitle(step.step_name)}
            </h4>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold text-slate-500 bg-slate-950 border border-slate-800 px-2 py-0.5 rounded">
              {step.duration_ms} ms
            </span>
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="p-1 rounded text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              title="Toggle raw metadata details"
            >
              {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-slate-400 mt-1 border-t border-slate-850 pt-2 font-medium">
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-500 block mb-0.5">Input Summary</span>
            <p className="line-clamp-2 leading-relaxed">{step.input_summary}</p>
          </div>
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-500 block mb-0.5">Output Summary</span>
            <p className="line-clamp-2 leading-relaxed text-slate-300">{step.output_summary}</p>
          </div>
        </div>

        {isOpen && (
          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 mt-2 animate-in slide-in-from-top-1 duration-150">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[9px] uppercase font-bold text-indigo-400 flex items-center gap-1">
                <Database className="w-3 h-3" /> Raw Node State Metadata
              </span>
              <span className="text-[8px] font-mono text-slate-600 font-medium select-none">
                READ-ONLY
              </span>
            </div>
            <pre className="text-[9px] font-mono font-medium text-slate-400 overflow-x-auto p-2 bg-slate-950 rounded scrollbar-thin">
              {JSON.stringify(step.metadata, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
