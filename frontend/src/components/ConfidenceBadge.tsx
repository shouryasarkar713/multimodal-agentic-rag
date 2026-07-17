import React from 'react';

interface ConfidenceBadgeProps {
  score: number;
}

export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  // Clamp score
  const clamped = Math.max(0, Math.min(1, score));
  const pct = Math.round(clamped * 100);

  let styleClass = '';
  let text = '';

  if (clamped >= 0.85) {
    styleClass = 'bg-primary/25 text-primary border-primary';
    text = 'HIGH CONF';
  } else if (clamped >= 0.6) {
    styleClass = 'bg-primary/15 text-primary/90 border-primary/50';
    text = 'MED CONF';
  } else {
    styleClass = 'bg-primary/5 text-primary/60 border-primary/20 border-dashed';
    text = 'LOW CONF';
  }

  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border text-[9px] font-bold font-tech-mono select-none uppercase tracking-wider ${styleClass}`}>
      <span>{text}: {pct}%</span>
    </div>
  );
}
