import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Sparkles, Database, UserCheck, Edit3, HelpCircle } from 'lucide-react';
import { FieldProvenance, FieldProvenanceSource } from '../api';
import { cn } from '../lib/utils';

interface FieldProvenanceBadgeProps {
  // The backend stores each tag as a plain string ("AI_EXTRACTED", ...); a richer
  // {source, ...} object is also accepted.
  provenance?: FieldProvenance | FieldProvenanceSource | string | null;
  size?: 'sm' | 'md';
  className?: string;
}

export const FieldProvenanceBadge: React.FC<FieldProvenanceBadgeProps> = ({
  provenance: rawProvenance,
  size = 'sm',
  className,
}) => {
  const provenance: FieldProvenance | null =
    typeof rawProvenance === 'string'
      ? { field_name: '', source: rawProvenance as FieldProvenanceSource }
      : rawProvenance ?? null;
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  // If no provenance provided by backend, render nothing (strict truthful absent state)
  if (!provenance || !provenance.source) {
    return null;
  }

  const getSourceConfig = (source: FieldProvenanceSource) => {
    switch (source) {
      case 'AI_EXTRACTED':
        return {
          label: t('fieldProvenance.AI_EXTRACTED', { defaultValue: 'AI Extracted' }),
          shortLabel: t('fieldProvenance.shortAI', { defaultValue: 'AI' }),
          icon: <Sparkles className="w-3 h-3 text-[#1565C0]" />,
          badgeClass:
            'bg-blue-50 dark:bg-blue-950/60 text-[#003087] dark:text-blue-300 border-blue-200/80 dark:border-blue-800/60',
          dotColor: 'bg-[#1565C0]',
        };
      case 'SCHEDULE_AUTO_FILLED':
        return {
          label: t('fieldProvenance.SCHEDULE_AUTO_FILLED', { defaultValue: 'Schedule Auto-Filled' }),
          shortLabel: t('fieldProvenance.shortSchedule', { defaultValue: 'Schedule' }),
          icon: <Database className="w-3 h-3 text-cyan-500" />,
          badgeClass:
            'bg-cyan-50 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 border-cyan-200/80 dark:border-cyan-800/60',
          dotColor: 'bg-cyan-500',
        };
      case 'ENGINEER_ENTERED':
        return {
          label: t('fieldProvenance.ENGINEER_ENTERED', { defaultValue: 'Engineer Entered' }),
          shortLabel: t('fieldProvenance.shortField', { defaultValue: 'Field' }),
          icon: <UserCheck className="w-3 h-3 text-blue-500" />,
          badgeClass:
            'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border-blue-200/80 dark:border-blue-800/60',
          dotColor: 'bg-blue-500',
        };
      case 'SUPERVISOR_EDITED':
        return {
          label: t('fieldProvenance.SUPERVISOR_EDITED', { defaultValue: 'Supervisor Edited' }),
          shortLabel: t('fieldProvenance.shortSupervisor', { defaultValue: 'Supervisor' }),
          icon: <Edit3 className="w-3 h-3 text-amber-500" />,
          badgeClass:
            'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-200/80 dark:border-amber-800/60',
          dotColor: 'bg-amber-500',
        };
      default:
        return {
          label: t('fieldProvenance.SYSTEM_PROVIDED', { defaultValue: 'System Provided' }),
          shortLabel: t('fieldProvenance.shortSystem', { defaultValue: 'System' }),
          icon: <HelpCircle className="w-3 h-3 text-slate-500" />,
          badgeClass:
            'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700',
          dotColor: 'bg-slate-400',
        };
    }
  };

  const config = getSourceConfig(provenance.source);

  return (
    <div className={cn('relative inline-flex items-center', className)}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setIsOpen(false)}
        aria-label={`Field provenance: ${config.label}`}
        aria-expanded={isOpen}
        className={cn(
          'inline-flex items-center gap-1 rounded-md border font-mono font-medium transition-all cursor-pointer focus:outline-hidden focus:ring-2 focus:ring-primary/40',
          size === 'sm' ? 'px-1.5 py-0.2 text-[10px]' : 'px-2 py-0.5 text-xs',
          config.badgeClass
        )}
      >
        {config.icon}
        <span>{config.shortLabel}</span>
      </button>

      {/* Accessible Floating Popover / Tooltip */}
      {isOpen && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 rounded-xl bg-slate-900/95 dark:bg-slate-950/95 text-white text-xs shadow-xl border border-slate-700 z-50 pointer-events-none backdrop-blur-xs animate-in fade-in zoom-in-95 duration-150"
        >
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-800 mb-1.5">
            <span className="font-semibold text-slate-200 flex items-center gap-1.5">
              <span className={cn('w-2 h-2 rounded-full', config.dotColor)} />
              {config.label}
            </span>
            {provenance.confidence != null && (
              <span className="font-mono text-[10px] text-emerald-400 font-bold">
                {Math.round(provenance.confidence * 100)}% conf
              </span>
            )}
          </div>

          <p className="text-[11px] text-slate-300 leading-snug">
            {provenance.source_detail || `Value provided via ${config.label.toLowerCase()} channel.`}
          </p>

          {(provenance.actor || provenance.timestamp) && (
            <div className="mt-2 pt-1.5 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400">
              {provenance.actor && <span>By: {provenance.actor}</span>}
              {provenance.timestamp && (
                <span>{new Date(provenance.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
