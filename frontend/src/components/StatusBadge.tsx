import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import {
  CheckCircle2,
  AlertTriangle,
  PauseCircle,
  XCircle,
  Search,
  AlertCircle,
  ShieldCheck,
  ShieldAlert,
  Bot,
  Calendar,
  HardHat,
  UserCheck,
  FileText,
  Clock,
  type LucideIcon,
} from 'lucide-react';

export type ClaimStatus =
  | 'EXTRACTED'
  | 'MATCHED'
  | 'UNMATCHED'
  | 'REVIEW_REQUIRED'
  | 'VALIDATED'
  | 'APPROVED'
  | 'EDITED'
  | 'REJECTED'
  | 'HOLD'
  | 'WARNING'
  | 'ERROR'
  | 'CORROBORATES'
  | 'CONTRADICTS'
  // Provenance states (prepared for Features 29-35)
  | 'AI_EXTRACTED'
  | 'SCHEDULE_AUTO_FILLED'
  | 'ENGINEER_ENTERED'
  | 'SUPERVISOR_EDITED';

interface StatusConfigItem {
  borderClass: string;
  textClass: string;
  bgClass: string;
  label: string;
  icon: LucideIcon;
}

const statusConfig: Record<ClaimStatus, StatusConfigItem> = {
  APPROVED: {
    borderClass: 'border-status-approved/40',
    textClass: 'text-status-approved',
    bgClass: 'bg-status-approved/10',
    label: 'Approved',
    icon: CheckCircle2,
  },
  EDITED: {
    borderClass: 'border-primary/40',
    textClass: 'text-primary',
    bgClass: 'bg-primary/10',
    label: 'Edited',
    icon: UserCheck,
  },
  VALIDATED: {
    borderClass: 'border-status-validated/40',
    textClass: 'text-status-validated',
    bgClass: 'bg-status-validated/10',
    label: 'Machine Validated',
    icon: ShieldCheck,
  },
  MATCHED: {
    borderClass: 'border-status-matched/40',
    textClass: 'text-status-matched',
    bgClass: 'bg-status-matched/10',
    label: 'Matched',
    icon: CheckCircle2,
  },
  REVIEW_REQUIRED: {
    borderClass: 'border-status-review/40',
    textClass: 'text-status-review',
    bgClass: 'bg-status-review/10',
    label: 'Review Required',
    icon: AlertTriangle,
  },
  UNMATCHED: {
    borderClass: 'border-status-unmatched/40',
    textClass: 'text-status-unmatched',
    bgClass: 'bg-status-unmatched/10',
    label: 'Unmatched',
    icon: Search,
  },
  HOLD: {
    borderClass: 'border-status-hold/40',
    textClass: 'text-status-hold',
    bgClass: 'bg-status-hold/10',
    label: 'On Hold',
    icon: PauseCircle,
  },
  REJECTED: {
    borderClass: 'border-status-rejected/40',
    textClass: 'text-status-rejected',
    bgClass: 'bg-status-rejected/10',
    label: 'Rejected',
    icon: XCircle,
  },
  EXTRACTED: {
    borderClass: 'border-status-extracted/40',
    textClass: 'text-status-extracted',
    bgClass: 'bg-status-extracted/10',
    label: 'Extracted',
    icon: FileText,
  },
  WARNING: {
    borderClass: 'border-status-warning/40',
    textClass: 'text-status-warning',
    bgClass: 'bg-status-warning/10',
    label: 'Warning',
    icon: AlertTriangle,
  },
  ERROR: {
    borderClass: 'border-status-error/40',
    textClass: 'text-status-error',
    bgClass: 'bg-status-error/10',
    label: 'Error',
    icon: AlertCircle,
  },
  CORROBORATES: {
    borderClass: 'border-status-corroborates/40',
    textClass: 'text-status-corroborates',
    bgClass: 'bg-status-corroborates/10',
    label: 'Corroborates',
    icon: ShieldCheck,
  },
  CONTRADICTS: {
    borderClass: 'border-status-contradicts/40',
    textClass: 'text-status-contradicts',
    bgClass: 'bg-status-contradicts/10',
    label: 'Contradicts',
    icon: ShieldAlert,
  },
  // Future Provenance States
  AI_EXTRACTED: {
    borderClass: 'border-prov-ai/40',
    textClass: 'text-prov-ai',
    bgClass: 'bg-prov-ai/10',
    label: 'AI Extracted',
    icon: Bot,
  },
  SCHEDULE_AUTO_FILLED: {
    borderClass: 'border-prov-schedule/40',
    textClass: 'text-prov-schedule',
    bgClass: 'bg-prov-schedule/10',
    label: 'Schedule Auto-Filled',
    icon: Calendar,
  },
  ENGINEER_ENTERED: {
    borderClass: 'border-prov-engineer/40',
    textClass: 'text-prov-engineer',
    bgClass: 'bg-prov-engineer/10',
    label: 'Site Engineer Entered',
    icon: HardHat,
  },
  SUPERVISOR_EDITED: {
    borderClass: 'border-prov-supervisor/40',
    textClass: 'text-prov-supervisor',
    bgClass: 'bg-prov-supervisor/10',
    label: 'Supervisor Override',
    icon: UserCheck,
  },
};

export const getStatusConfig = (status: string): StatusConfigItem => {
  const normalized = status?.toUpperCase() as ClaimStatus;
  return statusConfig[normalized] || {
    borderClass: 'border-border',
    textClass: 'text-muted-foreground',
    bgClass: 'bg-muted/50',
    label: status || 'Unknown',
    icon: Clock,
  };
};

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: string;
  variant?: 'badge' | 'dot' | 'outline' | 'pill';
  showIcon?: boolean;
  labelOverride?: string;
  size?: 'sm' | 'default' | 'lg';
}

export function StatusBadge({
  status,
  className,
  variant = 'badge',
  showIcon = true,
  labelOverride,
  size = 'default',
  ...props
}: StatusBadgeProps) {
  const { t } = useTranslation();
  const config = getStatusConfig(status);
  const Icon = config.icon;
  const normalized = status?.toUpperCase();
  const localizedLabel = normalized ? t(`status.${normalized}`, { defaultValue: config.label }) : config.label;
  const label = labelOverride || localizedLabel;

  const sizeClasses = {
    sm: 'text-[10px] px-1.5 py-0.5 gap-1',
    default: 'text-xs px-2.5 py-0.5 gap-1.5',
    lg: 'text-sm px-3 py-1 gap-2',
  }[size];

  const iconSizes = {
    sm: 'w-3 h-3',
    default: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  }[size];

  if (variant === 'dot') {
    return (
      <span className={cn('inline-flex items-center gap-1.5 font-medium', className)} {...props}>
        <span className={cn('h-2 w-2 rounded-full shrink-0', config.textClass.replace('text-', 'bg-'))} />
        <span className={cn('text-xs font-semibold', config.textClass)}>{label}</span>
      </span>
    );
  }

  if (variant === 'outline') {
    return (
      <span
        className={cn(
          'inline-flex items-center rounded-md border font-semibold tracking-wide uppercase',
          sizeClasses,
          config.borderClass,
          config.textClass,
          'bg-transparent',
          className
        )}
        {...props}
      >
        {showIcon && <Icon className={cn(iconSizes, 'shrink-0')} />}
        <span>{label}</span>
      </span>
    );
  }

  if (variant === 'pill') {
    return (
      <span
        className={cn(
          'inline-flex items-center rounded-full border font-semibold tracking-wide',
          sizeClasses,
          config.bgClass,
          config.borderClass,
          config.textClass,
          className
        )}
        {...props}
      >
        {showIcon && <Icon className={cn(iconSizes, 'shrink-0')} />}
        <span>{label}</span>
      </span>
    );
  }

  // Default 'badge'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border font-semibold tracking-wide transition-colors',
        sizeClasses,
        config.bgClass,
        config.borderClass,
        config.textClass,
        className
      )}
      {...props}
    >
      {showIcon && <Icon className={cn(iconSizes, 'shrink-0')} />}
      <span>{label}</span>
    </span>
  );
}

export default StatusBadge;
