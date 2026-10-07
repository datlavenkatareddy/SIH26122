import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import {
  FileUp,
  ScanLine,
  PenLine,
  Mic,
  FileSpreadsheet,
  HelpCircle,
  type LucideIcon,
} from 'lucide-react';
import { InputChannel } from '@/api';

export interface ProvenanceConfig {
  label: string;
  description: string;
  descKey?: string;
  icon: LucideIcon;
  badgeClass: string;
  subtleClass: string;
  outlineClass: string;
  iconClass: string;
}

export const PROVENANCE_CONFIGS: Record<InputChannel, ProvenanceConfig> = {
  TYPED_TEXT: {
    label: 'Typed Field Note',
    description: 'Manually typed by Site Engineer on site',
    descKey: 'descTypedText',
    icon: PenLine,
    badgeClass: 'bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30',
    subtleClass: 'bg-blue-500/10 text-blue-700 dark:text-blue-300 border-transparent',
    outlineClass: 'bg-transparent text-blue-700 dark:text-blue-300 border-blue-500/40',
    iconClass: 'text-blue-600 dark:text-blue-400',
  },
  VOICE: {
    label: 'Voice Recording',
    description: 'Dictated audio update transcribed via speech recognition',
    descKey: 'descVoice',
    icon: Mic,
    badgeClass: 'bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/30',
    subtleClass: 'bg-purple-500/10 text-purple-700 dark:text-purple-300 border-transparent',
    outlineClass: 'bg-transparent text-purple-700 dark:text-purple-300 border-purple-500/40',
    iconClass: 'text-purple-600 dark:text-purple-400',
  },
  FILE_UPLOAD: {
    label: 'Document Upload',
    description: 'Extracted from uploaded PDF, spreadsheet, or report',
    descKey: 'descFileUpload',
    icon: FileUp,
    badgeClass: 'bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-500/30',
    subtleClass: 'bg-amber-500/10 text-amber-800 dark:text-amber-300 border-transparent',
    outlineClass: 'bg-transparent text-amber-800 dark:text-amber-300 border-amber-500/40',
    iconClass: 'text-amber-600 dark:text-amber-400',
  },
  SCANNED_OCR: {
    label: 'Scanned Document / OCR',
    description: 'Digitized from physical site diary or paper record',
    descKey: 'descScannedOcr',
    icon: ScanLine,
    badgeClass: 'bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-500/30',
    subtleClass: 'bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-transparent',
    outlineClass: 'bg-transparent text-emerald-800 dark:text-emerald-300 border-emerald-500/40',
    iconClass: 'text-emerald-600 dark:text-emerald-400',
  },
  SCHEDULE_EXPORT: {
    label: 'Schedule Export',
    description: 'Ingested from Primavera P6 (.xer) or tabular export',
    descKey: 'descScheduleExport',
    icon: FileSpreadsheet,
    badgeClass: 'bg-sky-500/10 text-sky-800 dark:text-sky-300 border-sky-500/30',
    subtleClass: 'bg-sky-500/10 text-sky-800 dark:text-sky-300 border-transparent',
    outlineClass: 'bg-transparent text-sky-800 dark:text-sky-300 border-sky-500/40',
    iconClass: 'text-sky-600 dark:text-sky-400',
  },
};

const DEFAULT_PROVENANCE_CONFIG: ProvenanceConfig = {
  label: 'Unknown Origin',
  description: 'Unspecified ingestion channel',
  descKey: 'descUnknown',
  icon: HelpCircle,
  badgeClass: 'bg-muted text-muted-foreground border-border',
  subtleClass: 'bg-muted/60 text-muted-foreground border-transparent',
  outlineClass: 'bg-transparent text-muted-foreground border-border',
  iconClass: 'text-muted-foreground',
};

export function getProvenanceConfig(channel: InputChannel | string | null | undefined): ProvenanceConfig {
  if (!channel) return DEFAULT_PROVENANCE_CONFIG;
  return PROVENANCE_CONFIGS[channel as InputChannel] || {
    ...DEFAULT_PROVENANCE_CONFIG,
    label: String(channel).replace(/_/g, ' '),
  };
}

export interface ProvenanceBadgeProps {
  channel: InputChannel | string | null | undefined;
  variant?: 'badge' | 'subtle' | 'outline' | 'pill';
  size?: 'sm' | 'default' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export function ProvenanceBadge({
  channel,
  variant = 'badge',
  size = 'default',
  showIcon = true,
  className,
}: ProvenanceBadgeProps) {
  const { t } = useTranslation();
  const config = getProvenanceConfig(channel);
  const Icon = config.icon;

  const normalized = channel ? String(channel).toUpperCase() : 'UNKNOWN';
  const label = t(`provenance.${normalized}` as any, { defaultValue: config.label });
  const descKey = config.descKey;
  const description = descKey ? t(`provenance.${descKey}` as any, { defaultValue: config.description }) : config.description;

  const sizeClasses = {
    sm: 'text-[10px] px-1.5 py-0.5 gap-1 font-mono',
    default: 'text-xs px-2.5 py-1 gap-1.5 font-medium',
    lg: 'text-sm px-3 py-1.5 gap-2 font-medium',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    default: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  };

  let variantStyle = config.badgeClass;
  if (variant === 'subtle') variantStyle = config.subtleClass;
  if (variant === 'outline') variantStyle = config.outlineClass;

  return (
    <span
      role="status"
      aria-label={`Claim Origin: ${label}`}
      title={description}
      className={cn(
        'inline-flex items-center rounded-lg border font-sans select-none tracking-tight transition-colors shadow-2xs',
        variant === 'pill' ? 'rounded-full' : 'rounded-md',
        sizeClasses[size],
        variantStyle,
        className
      )}
    >
      {showIcon && <Icon className={cn(iconSizes[size], config.iconClass, 'shrink-0')} />}
      <span className="truncate">{label}</span>
    </span>
  );
}
