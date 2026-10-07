import React from 'react';
import { cn } from '@/lib/utils';

interface ConfidenceBarProps {
  score: number; // 0.0 to 1.0
  className?: string;
  showLabel?: boolean;
  label?: string;
}

export function ConfidenceBar({ score, className, showLabel = true, label = 'AI Match Confidence' }: ConfidenceBarProps) {
  const percentage = Math.min(Math.max(Math.round(score * 100), 0), 100);
  
  // Semantic threshold coloring
  const getBarColor = (pct: number) => {
    if (pct >= 80) return 'bg-emerald-600 dark:bg-emerald-500';
    if (pct >= 50) return 'bg-amber-500 dark:bg-amber-400';
    return 'bg-rose-500 dark:bg-rose-400';
  };

  const getTextColor = (pct: number) => {
    if (pct >= 80) return 'text-emerald-700 dark:text-emerald-400';
    if (pct >= 50) return 'text-amber-700 dark:text-amber-400';
    return 'text-rose-700 dark:text-rose-400';
  };

  return (
    <div className={cn("flex flex-col gap-1 w-full", className)}>
      {showLabel && (
        <div className="flex justify-between items-center text-[11px] font-medium text-muted-foreground">
          <span>{label}</span>
          <span className={cn("font-mono font-bold", getTextColor(percentage))}>
            {percentage}%
          </span>
        </div>
      )}
      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500 ease-out", getBarColor(percentage))}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export default ConfidenceBar;