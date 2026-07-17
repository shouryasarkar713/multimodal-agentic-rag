import React, { useState } from 'react';
import { Activity, Clock, Layers, ChevronDown, ChevronUp, Link as LinkIcon, Database } from 'lucide-react';
import { QueryTrace, TraceStep } from '../lib/types';

interface TraceTimelineProps {
  trace: QueryTrace;
}

export function TraceTimeline({ trace }: TraceTimelineProps) {
  return (
    <div className="w-full flex flex-col gap-6 font-sans">
      {/* Trace Overview Header Card */}
      <div className="p-6 rounded-sm border border-neutral-border bg-surface flex flex-col gap-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-sm bg-background border border-neutral-border text-primary shrink-0">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-base text-slate-100 font-editorial-serif">
                Agent Query Execution Trace
              </h2>
              <p className="text-[9px] font-tech-mono text-slate-500 uppercase tracking-wider mt-0.5">
                ID: {trace.id}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2 flex-wrap font-tech-mono text-[9px] uppercase tracking-wider font-bold">
            {/* Total Duration Badge */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm bg-background border border-neutral-border/50 text-slate-400">
              <Clock className="w-3.5 h-3.5 text-primary" />
              <span>Duration:</span>
              <span className="text-slate-200">{trace.total_duration_ms} ms</span>
            </div>
            {/* Classified Intent Badge */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm bg-background border border-primary/20 text-primary">
              <Layers className="w-3.5 h-3.5 text-primary" />
              <span>Intent:</span>
              <span className="text-primary font-bold">{trace.classified_intent || 'paper_qa'}</span>
            </div>
          </div>
        </div>

        {/* User Query Block */}
        <div className="bg-slate-950/40 border border-neutral-border p-4 rounded-sm">
          <div className="text-[9px] uppercase font-bold text-primary font-tech-mono tracking-widest mb-1.5">
            /trigger_query
          </div>
          <p className="text-xs md:text-sm font-semibold text-slate-200 italic font-editorial-serif">
            "{trace.user_query}"
          </p>
        </div>

        {/* LangSmith Trace Link */}
        {trace.langsmith_url && (
          <div className="flex items-center">
            <a
              href={trace.langsmith_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-sm bg-background text-slate-350 hover:text-primary hover:border-primary/50 border border-neutral-border transition-all text-xs font-bold font-tech-mono uppercase tracking-wider"
            >
              <LinkIcon className="w-3.5 h-3.5 text-primary" /> View Trace in LangSmith (External)
            </a>
          </div>
        )}
      </div>

      {/* Vertical Steps Timeline Tree */}
      <div className="flex flex-col relative pl-4 sm:pl-8 before:absolute before:left-8 before:top-4 before:bottom-4 before:w-0.5 before:bg-neutral-border/60 before:z-0">
        <h3 className="text-[10px] uppercase font-bold tracking-widest text-slate-500 mb-6 pl-4 select-none font-tech-mono">
          /execution_node_flow
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

  // Map step name to human-friendly title
  const getStepTitle = (name: string) => {
    return name
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Assign distinct border/accent classes to nodes
  const getStepColorClass = (name: string) => {
    switch (name) {
      case 'generator':
        return 'bg-primary border-primary text-primary';
      case 'hallucination_validator':
        return 'bg-red-500 border-red-500 text-red-400';
      default:
        return 'bg-slate-500 border-slate-500 text-slate-400';
    }
  };

  return (
    <div className="relative pb-8 pl-8 group">
      {/* Node Dot Icon */}
      <div className={`absolute left-[-24px] top-1.5 w-4 h-4 rounded-sm border-2 border-slate-950 flex items-center justify-center z-10 ${getStepColorClass(step.step_name).split(' ')[0]}`} />

      {/* Step Detail Card */}
      <div className="p-4 rounded-sm border border-neutral-border bg-surface hover:bg-background/25 transition-all duration-150 flex flex-col gap-2.5">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-tech-mono text-slate-500 font-bold">
              0{index + 1}
            </span>
            <h4 className="font-bold text-sm text-slate-200 font-editorial-serif">
              {getStepTitle(step.step_name)}
            </h4>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-tech-mono font-bold text-slate-500 bg-background border border-neutral-border/30 px-2 py-0.5 rounded-sm">
              {step.duration_ms} ms
            </span>
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="p-1 rounded-sm text-slate-500 hover:text-slate-255 hover:bg-background transition-colors border border-transparent hover:border-neutral-border/30"
              title="Toggle raw metadata details"
            >
              {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Input/Output Excerpt Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-slate-400 mt-1 border-t border-neutral-border/20 pt-2 font-grotesk-sans font-medium">
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-500 font-tech-mono block mb-0.5">/input_summary</span>
            <p className="line-clamp-2 leading-relaxed">{step.input_summary}</p>
          </div>
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-500 font-tech-mono block mb-0.5">/output_summary</span>
            <p className="line-clamp-2 leading-relaxed text-slate-350">{step.output_summary}</p>
          </div>
        </div>

        {/* Raw Metadata Details JSON Viewer */}
        {isOpen && (
          <div className="bg-slate-950/60 border border-neutral-border/50 rounded-sm p-3 mt-2 animate-in slide-in-from-top-1 duration-150 font-sans">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[9px] uppercase font-bold text-primary font-tech-mono flex items-center gap-1">
                <Database className="w-3 h-3 text-primary/80" /> /raw_node_state_metadata
              </span>
              <span className="text-[8px] font-tech-mono text-slate-650 font-bold select-none">
                READ-ONLY
              </span>
            </div>
            <pre className="text-[9px] font-tech-mono text-slate-400 overflow-x-auto p-2 bg-slate-950 rounded-sm border border-neutral-border/20 scrollbar-thin">
              {JSON.stringify(step.metadata, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
