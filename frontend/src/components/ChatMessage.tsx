import React, { useState } from 'react';
import Link from 'next/link';
import { MessageSquare, Bot, User, Share2, FileText, Activity } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message, Citation } from '../lib/types';
import { ConfidenceBadge } from './ConfidenceBadge';
import { ExportButton } from './ExportButton';
import { CitationCard } from './CitationCard';
import { FigureViewer } from './FigureViewer';

interface ChatMessageProps {
  message: Message;
}

const GREEK_MAP: Record<string, string> = {
  alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ε', varepsilon: 'ε',
  zeta: 'ζ', eta: 'η', theta: 'θ', vartheta: 'θ', iota: 'ι', kappa: 'κ',
  lambda: 'λ', mu: 'μ', nu: 'ν', xi: 'ξ', pi: 'π', varpi: 'ϖ', rho: 'ρ',
  varrho: 'ϱ', sigma: 'σ', varsigma: 'ς', tau: 'τ', upsilon: 'υ', phi: 'φ',
  varphi: 'ϕ', chi: 'χ', psi: 'ψ', omega: 'ω',
  Gamma: 'Γ', Delta: 'Δ', Theta: 'Θ', Lambda: 'Λ', Xi: 'Ξ', Pi: 'Π',
  Sigma: 'Σ', Upsilon: 'Υ', Phi: 'Φ', Psi: 'Ψ', Omega: 'Ω',
};

const SYMBOL_MAP: Record<string, string> = {
  le: '≤', leq: '≤', ge: '≥', geq: '≥', ne: '≠', neq: '≠',
  approx: '≈', in: '∈', notin: '∉', ni: '∋', subset: '⊂',
  subseteq: '⊆', supset: '⊃', supseteq: '⊇', cap: '∩', cup: '∪',
  setminus: '∖', times: '×', cdot: '·', pm: '±', mp: '∓',
  to: '→', rightarrow: '→', leftarrow: '←', leftrightarrow: '↔',
  implies: '⇒', iff: '⇔', infty: '∞', forall: '∀', exists: '∃',
  nabla: '∇', partial: '∂', angle: '∠', circ: '∘',
  'mathbb{R}': 'ℝ', 'mathbb{Z}': 'ℤ', 'mathbb{N}': 'ℕ', 'mathbb{Q}': 'ℚ', 'mathbb{C}': 'ℂ',
};

const SUBSCRIPTS: Record<string, string> = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
  '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
  '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
  'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
  'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
  'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
  'v': 'ᵥ', 'x': 'ₓ',
};

const SUPERSCRIPTS: Record<string, string> = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
  '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
  '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
  'i': 'ⁱ', 'j': 'ʲ', 'n': 'ⁿ', 't': 'ᵗ',
};

function formatMathFallback(tex: string): string {
  let s = tex;
  for (const [name, sym] of Object.entries(GREEK_MAP)) {
    s = s.replace(new RegExp(`\\\\${name}\\b`, 'g'), sym);
  }
  for (const [name, sym] of Object.entries(SYMBOL_MAP)) {
    s = s.replace(new RegExp(`\\\\${name}\\b`, 'g'), sym);
  }
  s = s.replace(/'/g, '′');
  s = s.replace(/_\{([0-9a-z\+\-\(\)]+)\}/gi, (_, content) => {
    let converted = '';
    for (const ch of content) converted += SUBSCRIPTS[ch.toLowerCase()] || ch;
    return converted;
  });
  s = s.replace(/_([0-9a-z\+\-\(\)])/gi, (_, char) => SUBSCRIPTS[char.toLowerCase()] || `_${char}`);
  s = s.replace(/\^\{([0-9a-z\+\-\(\)]+)\}/gi, (_, content) => {
    let converted = '';
    for (const ch of content) converted += SUPERSCRIPTS[ch.toLowerCase()] || ch;
    return converted;
  });
  s = s.replace(/\^([0-9a-z\+\-\(\)])/gi, (_, char) => SUPERSCRIPTS[char.toLowerCase()] || `^${char}`);
  s = s.replace(/\\(?:text|mathrm|mathbf|mathit)\{([^}]+)\}/g, '$1');
  s = s.replace(/[\{\}]/g, '');
  s = s.replace(/\\/g, '');
  return s;
}

function MathRenderer({ math, displayMode }: { math: string; displayMode?: boolean }) {
  const [renderedHtml, setRenderedHtml] = useState<string | null>(null);

  React.useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).katex) {
      try {
        const html = (window as any).katex.renderToString(math, {
          displayMode: !!displayMode,
          throwOnError: false,
        });
        setRenderedHtml(html);
      } catch {
        // Fallback to formatted unicode
      }
    }
  }, [math, displayMode]);

  if (renderedHtml) {
    return (
      <span
        className={displayMode ? "block my-2 text-center overflow-x-auto text-primary" : "inline-block px-1 align-baseline"}
        dangerouslySetInnerHTML={{ __html: renderedHtml }}
      />
    );
  }

  const fallback = formatMathFallback(math);
  return (
    <span
      className={`font-serif italic text-cyan-300 font-semibold tracking-wide ${
        displayMode ? "block my-2 text-center text-sm py-1 bg-slate-900/40 rounded px-2" : "inline-block px-0.5"
      }`}
      title={math}
    >
      {fallback}
    </span>
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const hasCitations = message.citations && message.citations.length > 0;
  const hasFigures = message.figure_refs && message.figure_refs.length > 0;

  const processTextWithMathAndCitations = (text: string) => {
    // Matches display math ($$...$$), inline math ($...$), citations ([N], [p. N], (p. N)), and figure refs
    const tokenRegex = /(\$\$[\s\S]+?\$\$|\$(?:\\\$|[^\$\n])+\$|\[\d+\]|\[p\.?\s*\d+\]|\(p\.?\s*\d+\)|\[citation not found\]|\[Figure(?:\s*\d+)?\s*from\s*(?:source\s*)?\d+\])/gi;
    const parts = text.split(tokenRegex);
    if (parts.length === 1) {
      // Clean any isolated latex commands in plain text
      return formatMathFallback(text);
    }

    return parts.map((part, idx) => {
      if (!part) return null;

      // 1. Display Math: $$ ... $$
      if (part.startsWith('$$') && part.endsWith('$$') && part.length >= 4) {
        const math = part.slice(2, -2).trim();
        return <MathRenderer key={idx} math={math} displayMode={true} />;
      }

      // 2. Inline Math: $ ... $
      if (part.startsWith('$') && part.endsWith('$') && part.length >= 2) {
        const math = part.slice(1, -1).trim();
        return <MathRenderer key={idx} math={math} displayMode={false} />;
      }

      // 3. Citations: [N], [p. N], (p. N)
      if ((part.startsWith('[') && part.endsWith(']')) || (part.startsWith('(') && part.endsWith(')'))) {
        if (part === '[citation not found]') {
          return (
            <span
              key={idx}
              className="inline-block px-1.5 py-0.5 mx-0.5 rounded-sm bg-red-500/10 text-red-400 border border-red-500/20 text-[8px] font-tech-mono font-bold select-none uppercase tracking-wide animate-pulse"
            >
              citation not found
            </span>
          );
        }
        // Check if figure reference like [Figure from source 1] or [Figure 2 from source 1] (case-insensitive)
        const figMatch = part.match(/[\[\(]Figure(?:\s*(\d+))?\s*from\s*(?:source\s*)?(\d+)[\]\)]/i);
        if (figMatch) {
          const figSourceNum = parseInt(figMatch[2] || figMatch[1], 10);
          return (
            <span
              key={idx}
              onClick={() => {
                const figEl = document.getElementById(`figure-card-${figSourceNum - 1}`) || document.getElementById('figure-card-0') || document.getElementById(`citation-card-${figSourceNum - 1}`) || document.getElementById('citation-card-0');
                if (figEl) {
                  figEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                  figEl.classList.add('ring-1', 'ring-primary');
                  setTimeout(() => figEl.classList.remove('ring-1', 'ring-primary'), 1500);
                }
              }}
              className="inline-block px-1.5 py-0.5 mx-0.5 rounded-sm bg-primary/15 text-primary border border-primary/30 hover:bg-primary hover:text-slate-950 transition-colors text-[9px] font-tech-mono font-bold select-none cursor-pointer tracking-wider"
              title="Click to view referenced figure"
            >
              {part}
            </span>
          );
        }

        // Check if page citation like [p. 1] or (p. 1)
        const pageMatch = part.match(/[\[\(]p\.?\s*(\d+)[\]\)]/i);
        let cardTargetIdx = 0;
        let matchedCitation: Citation | null = null;

        if (pageMatch) {
          const pageNum = parseInt(pageMatch[1], 10);
          const foundIdx = (message.citations || []).findIndex(c => c.page_number === pageNum);
          if (foundIdx !== -1 && message.citations) {
            cardTargetIdx = foundIdx;
            matchedCitation = message.citations[foundIdx];
          } else if (message.citations && message.citations.length > 0) {
            matchedCitation = message.citations[0];
          }
        } else if (part.startsWith('[') && part.endsWith(']')) {
          const num = parseInt(part.slice(1, -1), 10);
          if (!isNaN(num)) {
            cardTargetIdx = (message.citations && num - 1 < message.citations.length && num - 1 >= 0)
              ? num - 1
              : 0;
            matchedCitation = message.citations?.[num - 1] || (message.citations && message.citations.length > 0 ? message.citations[0] : null);
          }
        }

        if (matchedCitation) {
          return (
            <span
              key={idx}
              onClick={() => {
                const el = document.getElementById(`citation-card-${cardTargetIdx}`);
                if (el) {
                  el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                  el.classList.add('ring-1', 'ring-primary');
                  setTimeout(() => el.classList.remove('ring-1', 'ring-primary'), 1500);
                }
              }}
              className="inline-block px-1.5 py-0.5 mx-0.5 rounded-sm bg-primary/10 text-primary border border-primary/20 hover:bg-primary hover:text-slate-950 transition-colors text-[8px] font-tech-mono font-bold select-none cursor-pointer tracking-wider"
              title={`Source: ${matchedCitation.document_title}, Page ${matchedCitation.page_number}`}
            >
              {part}
            </span>
          );
        }
        return (
          <span
            key={idx}
            className="inline-block px-1.5 py-0.5 mx-0.5 rounded-sm bg-slate-800 text-slate-400 text-[8px] font-tech-mono font-bold select-none tracking-wider"
          >
            {part}
          </span>
        );
      }

      // 4. Plain text: format any lone LaTeX backslash symbols
      return formatMathFallback(part);
    });
  };

  const renderWithCitations = (node: React.ReactNode): React.ReactNode => {
    if (typeof node === 'string') {
      return processTextWithMathAndCitations(node);
    }
    if (React.isValidElement(node)) {
      if (node.props.children) {
        return React.cloneElement(
          node,
          // @ts-ignore
          node.props,
          React.Children.map(node.props.children, child => renderWithCitations(child))
        );
      }
    }
    return node;
  };

  const components = {
    p: ({ children }: any) => <p className="leading-relaxed font-editorial-serif text-slate-200 text-sm md:text-base font-medium mb-4">{React.Children.map(children, child => renderWithCitations(child))}</p>,
    li: ({ children }: any) => <li className="leading-relaxed font-sans text-slate-350 text-xs md:text-sm mb-1.5 list-disc ml-5">{React.Children.map(children, child => renderWithCitations(child))}</li>,
    td: ({ children }: any) => <td className="border border-neutral-border/40 p-2.5 text-xs font-sans text-slate-250">{React.Children.map(children, child => renderWithCitations(child))}</td>,
    th: ({ children }: any) => <th className="border border-neutral-border/45 bg-slate-900/50 p-2.5 text-xs font-tech-mono font-bold text-slate-350 uppercase tracking-wider">{React.Children.map(children, child => renderWithCitations(child))}</th>,
    h1: ({ children }: any) => <h1 className="font-editorial-serif text-xl md:text-2xl font-bold text-slate-100 mt-6 mb-3 border-b border-neutral-border/20 pb-1">{children}</h1>,
    h2: ({ children }: any) => <h2 className="font-editorial-serif text-lg md:text-xl font-bold text-slate-100 mt-5 mb-2.5">{children}</h2>,
    h3: ({ children }: any) => <h3 className="font-editorial-serif text-base md:text-lg font-bold text-slate-200 mt-4 mb-2">{children}</h3>,
    h4: ({ children }: any) => <h4 className="font-editorial-serif text-sm md:text-base font-bold text-slate-200 mt-3 mb-1.5">{children}</h4>,
    table: ({ children }: any) => (
      <div className="overflow-x-auto my-5 border border-neutral-border/40 rounded-sm">
        <table className="min-w-full border-collapse text-left">{children}</table>
      </div>
    ),
    pre: ({ children }: any) => <pre className="bg-slate-950/80 border border-neutral-border/40 p-4 rounded-sm my-4 overflow-x-auto font-tech-mono text-xs text-slate-300">{children}</pre>,
    code: ({ children }: any) => <code className="bg-slate-900/50 border border-neutral-border/20 px-1 py-0.5 rounded-sm font-tech-mono text-xs text-primary">{children}</code>
  };

  // Render text content and highlight citations/figures
  const renderMessageBody = (text: string) => {
    if (isUser) {
      const isFigureQuery = text.includes('[EXPLAIN_FIGURE:');
      const cleanText = text.replace(/\[EXPLAIN_FIGURE:\s*[a-f0-9\-]+\]\s*/i, '');
      const displayText = formatMathFallback(cleanText);

      return (
        <div className="flex flex-col gap-1 items-end">
          {isFigureQuery && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm bg-primary/15 border border-primary/30 text-primary text-[8px] font-tech-mono font-bold uppercase tracking-wider mb-1">
              Figure Analysis Query
            </span>
          )}
          <p className="whitespace-pre-wrap leading-relaxed font-editorial-serif text-slate-200 text-sm md:text-base font-medium text-right">
            {displayText}
          </p>
        </div>
      );
    }

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {text}
      </ReactMarkdown>
    );
  };

  return (
    <div className={`flex w-full gap-4 py-6 px-4 md:px-6 border-b border-neutral-border/40 transition-colors duration-150 ${
      isUser 
        ? 'bg-background/10 border-neutral-border/20 justify-end' 
        : 'bg-surface/20 border-neutral-border/20 justify-start'
    }`}>
      <div className={`flex gap-4 max-w-4xl w-full ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Role Icon Avatar */}
        <div className={`w-8 h-8 rounded-sm border flex items-center justify-center shrink-0 shadow-sm ${
          isUser 
            ? 'bg-slate-950 border-neutral-border text-slate-500' 
            : 'bg-background border-primary/30 text-primary'
        }`}>
          {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
        </div>

        {/* Message Content Container */}
        <div className="flex flex-col gap-3 flex-1 min-w-0 font-sans">
          {/* Header Metadata */}
          {!isUser && (
            <div className="flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex items-center gap-2">
                <span className="font-bold text-[10px] text-primary font-tech-mono uppercase tracking-widest">
                  Copilot Response
                </span>
                {message.confidence !== undefined && message.confidence !== null && (
                  <ConfidenceBadge score={message.confidence} />
                )}
              </div>
              
              {/* Top Right Trace Trigger */}
              {message.trace_id && (
                <Link
                  href={`/trace/${message.trace_id}`}
                  className="inline-flex items-center gap-1 text-[9px] font-bold font-tech-mono text-slate-500 hover:text-primary transition-colors uppercase tracking-wider border border-neutral-border/25 bg-background/20 px-2 py-0.5 rounded-sm"
                >
                  <Activity className="w-3.5 h-3.5 text-primary/80" /> Trace node
                </Link>
              )}
            </div>
          )}

          {isUser && (
            <span className="font-bold text-[10px] text-slate-500 font-tech-mono uppercase tracking-widest">
              Index query trigger
            </span>
          )}

          {/* Text Body */}
          <div className={`text-slate-200 leading-relaxed ${isUser ? 'border-l-2 border-primary/70 pl-4 py-1 max-w-2xl self-end italic font-grotesk-sans font-medium text-xs md:text-sm' : ''}`}>
            {renderMessageBody(message.content)}
          </div>

          {/* Side-Scrollable Citations List */}
          {!isUser && hasCitations && (
            <div className="flex flex-col gap-2 mt-3 border-t border-neutral-border/20 pt-4">
              <span className="text-[10px] font-bold text-slate-500 font-tech-mono uppercase tracking-widest pl-1">
                Source Citations ({message.citations?.length || 0})
              </span>
              <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-800">
                {message.citations?.map((cit, idx) => (
                  <div id={`citation-card-${idx}`} key={cit.chunk_id || idx} className="transition-all duration-300">
                    <CitationCard citation={cit} index={idx + 1} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Side-Scrollable Figures List */}
          {!isUser && hasFigures && (
            <div className="flex flex-col gap-2 mt-3 border-t border-neutral-border/20 pt-4">
              <span className="text-[10px] font-bold text-slate-500 font-tech-mono uppercase tracking-widest pl-1">
                Referenced Figures
              </span>
              <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-800">
                {message.figure_refs?.map((fig, fIdx) => (
                  <div key={fig.chunk_id || fIdx} id={`figure-card-${fIdx}`} className="transition-all duration-300">
                    <FigureViewer figure={fig} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Footer Actions Row */}
          {!isUser && (
            <div className="flex items-center justify-between mt-4 border-t border-neutral-border/20 pt-3">
              <div className="flex items-center gap-2">
                <ExportButton messageId={message.id} />
              </div>
              <span className="text-[9px] font-tech-mono text-slate-500 font-bold select-none uppercase">
                {message.created_at ? new Date(message.created_at).toLocaleTimeString() : ''}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
