import React from 'react';
import {
  FileText,
  Sparkles,
  Target,
  ShieldCheck,
  AlertTriangle,
  UserCheck,
  CheckCircle2,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ExecutionEvent, CandidateMatch, ValidationIssue, ConflictRecord } from '@/api';

interface ProvenancePipelineStepperProps {
  event: ExecutionEvent;
  candidates: CandidateMatch[];
  issues: ValidationIssue[];
  conflicts: ConflictRecord[];
  decisionCommitted: boolean;
}

export function ProvenancePipelineStepper({
  event,
  candidates,
  issues,
  conflicts,
  decisionCommitted,
}: ProvenancePipelineStepperProps) {
  const topCandidate = candidates[0];
  const hasFatalIssues = issues.some((i) => i.severity === 'ERROR');
  const hasConflicts = conflicts.length > 0;

  const steps = [
    {
      id: 'claim',
      label: 'Field Claim',
      subtitle: event.input_channel || 'Raw Claim',
      icon: FileText,
      status: 'completed',
      detail: event.event_date,
    },
    {
      id: 'extract',
      label: 'AI Extraction',
      subtitle: event.claimed_pct !== null ? `${event.claimed_pct}%` : 'Extracted',
      icon: Sparkles,
      status: 'completed',
      detail: event.discipline || 'Assisted',
    },
    {
      id: 'match',
      label: 'Activity Match',
      subtitle: topCandidate
        ? `${Math.round(topCandidate.composite_confidence * 100)}% Match`
        : (event.matched_activity_id || 'Matched'),
      icon: Target,
      status: topCandidate ? 'completed' : 'active',
      detail: topCandidate?.activity_id || event.matched_activity_id,
    },
    {
      id: 'validation',
      label: 'Validation',
      subtitle: issues.length === 0 ? 'Passed' : `${issues.length} Flagged`,
      icon: hasFatalIssues ? AlertTriangle : ShieldCheck,
      status: hasFatalIssues ? 'warning' : 'completed',
      detail: issues.length === 0 ? 'Zero flags' : `${issues.length} warnings`,
    },
    {
      id: 'evidence',
      label: 'Evidence / Conflict',
      subtitle: hasConflicts ? 'Conflict Alert' : 'Verified Evidence',
      icon: hasConflicts ? ShieldAlert : FileText,
      status: hasConflicts ? 'warning' : 'completed',
      detail: hasConflicts ? `${conflicts.length} open` : 'Traceable',
    },
    {
      id: 'decision',
      label: 'Supervisor Review',
      subtitle: decisionCommitted ? 'Committed' : 'Human Authority',
      icon: UserCheck,
      status: decisionCommitted ? 'completed' : 'active',
      detail: decisionCommitted ? 'Logged' : 'Awaiting Action',
    },
    {
      id: 'actual',
      label: 'Approved Actual',
      subtitle: decisionCommitted ? 'Committed to P6' : 'Gated by Supervisor',
      icon: CheckCircle2,
      status: decisionCommitted ? 'completed' : 'pending',
      detail: decisionCommitted ? 'Permanent' : 'Read-Only Gate',
    },
  ];

  return (
    <div className="p-3 bg-white dark:bg-[#001E60]/80 rounded-2xl border border-slate-200 dark:border-blue-900/50 shadow-xs">
      <div className="flex items-center justify-between gap-2 overflow-x-auto pb-1">
        {steps.map((step, idx) => {
          const Icon = step.icon;
          const isCompleted = step.status === 'completed';
          const isActive = step.status === 'active';
          const isWarning = step.status === 'warning';

          return (
            <React.Fragment key={step.id}>
              <div className="flex flex-col items-center text-center min-w-[100px] flex-1 px-1">
                <div
                  className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center transition-all mb-1.5',
                    isActive
                      ? 'bg-[#FC4C02] text-white shadow-md shadow-[#FC4C02]/20 ring-2 ring-[#FC4C02]/30'
                      : isWarning
                      ? 'bg-rose-100 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 border border-rose-300'
                      : isCompleted
                      ? 'bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                      : 'bg-slate-100 dark:bg-[#001438] text-slate-400 border border-slate-200 dark:border-slate-800'
                  )}
                >
                  <Icon className="w-4 h-4" />
                </div>

                <span
                  className={cn(
                    'text-[11px] font-bold tracking-tight truncate w-full',
                    isActive
                      ? 'text-[#FC4C02]'
                      : isWarning
                      ? 'text-rose-600 dark:text-rose-400'
                      : isCompleted
                      ? 'text-slate-800 dark:text-slate-200'
                      : 'text-slate-400 dark:text-slate-500'
                  )}
                >
                  {step.label}
                </span>

                <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 truncate w-full">
                  {step.subtitle}
                </span>
              </div>

              {idx < steps.length - 1 && (
                <ChevronRight className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600 shrink-0 mb-3" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
