import React, { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { api } from '../lib/api';

interface ExportButtonProps {
  messageId: string;
}

export function ExportButton({ messageId }: ExportButtonProps) {
  const [downloading, setDownloading] = useState<boolean>(false);

  const handleExport = async () => {
    try {
      setDownloading(true);
      const blob = await api.exportMarkdown(messageId);
      
      // Create download link in browser
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `research_export_${messageId.substring(0, 8)}.md`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export markdown', err);
      alert('Failed to export message: ' + (err instanceof Error ? err.message : 'unknown error'));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={downloading}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm border border-neutral-border bg-background hover:bg-surface hover:text-primary hover:border-primary/50 text-[9px] font-bold font-tech-mono uppercase tracking-wider text-slate-400 transition-all duration-150"
      title="Download message and sources as markdown file"
    >
      {downloading ? (
        <Loader2 className="w-3 h-3 animate-spin text-primary" />
      ) : (
        <Download className="w-3 h-3" />
      )}
      <span>Export</span>
    </button>
  );
}
