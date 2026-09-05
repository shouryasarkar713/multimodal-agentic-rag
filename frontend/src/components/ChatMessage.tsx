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
    const tokenRegex = /(\$\$[\s\S]+?\$\$|\$(?:\\\$|[^\$\n])+\$|\[\d+\]|\[p\.?\s*\d+\]|\(p\.?\s*\d+\)|\[citation not found\]|\[Figure from source \d+\])/gi;
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
        if (part.startsWith('[Figure from source')) {
          return (
            <span
              key={idx}
              className="inline-block px-1.5 py-0.5 mx-0.5 rounded-sm bg-primary/10 text-primary border border-primary/20 text-[8px] font-tech-mono font-bold select-none cursor-default uppercase tracking-wide"
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
          if (foundIdx !== -1) {
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
          {},
          React.Children.map(node.props.children, renderWithCitations)
        );
      }
    }
    return node;
  };

  return (
    <div
      className={`group relative flex gap-4 px-6 py-6 transition-colors duration-200 ${
        isUser
          ? 'bg-slate-900/40 border-b border-border/20'
          : 'bg-slate-900/10 border-b border-border/40 hover:bg-slate-900/20'
      }`}
    >
      <div className="flex-shrink-0 pt-0.5">
        <div
          className={`flex h-9 w-9 items-center justify-center rounded-sm border ${
            isUser
              ? 'bg-slate-800/80 border-border text-slate-300'
              : 'bg-primary/10 border-primary/30 text-primary shadow-[0_0_12px_rgba(0,240,255,0.15)]'
          }`}
        >
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </div>
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-tech-mono text-[11px] font-bold tracking-wider text-slate-300 uppercase">
              {isUser ? 'Researcher' : 'Copilot Response'}
            </span>
            {!isUser && message.confidence !== undefined && (
              <ConfidenceBadge score={message.confidence} />
            )}
          </div>
          {!isUser && message.trace_id && (
            <Link
              href={`/traces/${message.trace_id}`}
              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border border-primary/20 bg-primary/5 hover:bg-primary/10 text-[10px] font-tech-mono text-primary transition-colors tracking-wider uppercase"
              title="View Agent Execution Trace"
            >
              <Activity className="h-3 w-3" />
              <span>Trace Node</span>
            </Link>
          )}
        </div>

        <div className="prose prose-invert max-w-none text-slate-300 text-sm leading-relaxed font-sans prose-headings:font-serif prose-headings:tracking-tight prose-headings:text-slate-100 prose-a:text-primary prose-a:no-underline hover:prose-a:underline prose-code:text-primary prose-code:bg-primary/5 prose-code:border prose-code:border-primary/20 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-sm prose-code:font-tech-mono prose-code:text-xs">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="mb-3 leading-relaxed">{React.Children.map(children, renderWithCitations)}</p>,
              li: ({ children }) => <li className="mb-1 leading-relaxed">{React.Children.map(children, renderWithCitations)}</li>,
              h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-2 text-slate-100">{React.Children.map(children, renderWithCitations)}</h1>,
              h2: ({ children }) => <h2 className="text-lg font-semibold mt-3 mb-2 text-slate-200">{React.Children.map(children, renderWithCitations)}</h2>,
              h3: ({ children }) => <h3 className="text-base font-semibold mt-2 mb-1 text-slate-200">{React.Children.map(children, renderWithCitations)}</h3>,
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-primary/40 pl-4 my-2 italic text-slate-400 bg-primary/5 py-1 rounded-r-sm">
                  {React.Children.map(children, renderWithCitations)}
                </blockquote>
              ),
              table: ({ children }) => (
                <div className="overflow-x-auto my-4 rounded-sm border border-border/40 bg-slate-900/40">
                  <table className="min-w-full divide-y divide-border/40 text-left text-xs font-sans">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => <thead className="bg-slate-900/80 font-tech-mono text-slate-300 tracking-wider uppercase">{children}</thead>,
              tbody: ({ children }) => <tbody className="divide-y divide-border/20">{children}</tbody>,
              tr: ({ children }) => <tr className="hover:bg-slate-800/30 transition-colors">{children}</tr>,
              th: ({ children }) => <th className="px-3 py-2 font-bold">{children}</th>,
              td: ({ children }) => <td className="px-3 py-2 text-slate-300">{React.Children.map(children, renderWithCitations)}</td>,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Figures section */}
        {hasFigures && (
          <div className="pt-2">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-tech-mono text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                Referenced Figures ({message.figure_refs!.length})
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {message.figure_refs!.map((fig, idx) => (
                <FigureViewer
                  key={idx}
                  imagePath={fig.image_path}
                  caption={fig.caption}
                  pageNumber={fig.page_number}
                />
              ))}
            </div>
          </div>
        )}

        {/* Citations section */}
        {hasCitations && (
          <div className="pt-2 border-t border-border/20">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-3.5 w-3.5 text-primary" />
              <span className="font-tech-mono text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Source Citations ({message.citations!.length})
              </span>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-border">
              {message.citations!.map((cit, idx) => (
                <div key={idx} id={`citation-card-${idx}`} className="flex-shrink-0 transition-all duration-300 rounded-sm">
                  <CitationCard citation={cit} index={idx + 1} />
                </div>
              ))}
            </div>
          </div>
        )}

        {!isUser && (
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-3 text-[11px] font-tech-mono text-slate-500">
              <span>{new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <ExportButton content={message.content} />
          </div>
        )}
      </div>
    </div>
  );
}
