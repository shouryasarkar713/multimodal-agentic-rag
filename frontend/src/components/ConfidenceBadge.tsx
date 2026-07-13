import React from 'react';
import { ShieldCheck, ShieldAlert, Shield } from 'lucide-react';

interface ConfidenceBadgeProps {
  score: number;
}

export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  const clamped = Math.max(0, Math.min(1, score));
  const pct = Math.round(clamped * 100);

  let colorClass = '';
  let Icon = Shield;
  let text = '';

  if (clamped >= 0.85) {
    colorClass = 'bg-green-500/10 text-green-400 border-green-500/20';
    Icon = ShieldCheck;
    text = 'High Confidence';
  } else if (clamped >= 0.6) {
    colorClass = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    Icon = Shield;
    text = 'Medium Confidence';
  } else {
    colorClass = 'bg-red-500/10 text-red-400 border-red-500/20';
    Icon = ShieldAlert;
    text = 'Low Confidence';
  }

  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-[10px] font-extrabold select-none ${colorClass}`}>
      <Icon className="w-3.5 h-3.5" />
      <span>{text}: {pct}%</span>
    </div>
  );
}
