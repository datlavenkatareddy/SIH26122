import React, { useMemo } from 'react';
import { ImpactPreviewResult } from '@/api';
import {
  Calendar,
  Clock,
  ArrowRight,
  AlertTriangle,
  Info,
  ShieldCheck,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ImpactTimelineViewProps {
  data: ImpactPreviewResult;
  onSelectActivity?: (id: string) => void;
}

interface TimelineItem {
  id: string;
  name: string;
  depth: number;
  isOrigin: boolean;
  relationship: string;
  baselineStart: string;
  baselineFinish: string;
  shiftedStart: string;
  shiftedFinish: string;
  grossDelay: number;
  netDelay: number;
  absorbedDelay: number;
  floatVal: number | null;
  floatStatus: string;
  isCompleted: boolean;
  uncertainty: boolean;
  startOffsetDays: number;
  plannedDurationDays: number;
  netShiftDays: number;
}

export function ImpactTimelineView({ data, onSelectActivity }: ImpactTimelineViewProps) {
  const { timelineItems, minTimestamp, totalSpanDays } = useMemo(() => {
    const items: TimelineItem[] = [];

    // Parse helper
    const parse = (d?: string | null) => {
      if (!d) return null;
      const ts = Date.parse(d.slice(0, 10));
      return isNaN(ts) ? null : ts;
    };

    let earliest = Infinity;
    let latest = -Infinity;

    // Origin item
    const origStart = data.planned_start || '';
    const origFin = data.planned_finish || '';
    const origShiftFin = data.shifted_finish || '';

    const origStartTs = parse(origStart) || Date.now();
    const origFinTs = parse(origFin) || origStartTs + 7 * 86400000;
    const origShiftFinTs = parse(origShiftFin) || origFinTs + data.delay_days * 86400000;

    earliest = Math.min(earliest, origStartTs);
    latest = Math.max(latest, origFinTs, origShiftFinTs);

    // Process each successor impact
    for (const imp of data.impacts) {
      const bStartTs = parse(imp.original_earliest_start) || origFinTs;
      const bFinTs =
        parse(imp.original_planned_finish) || bStartTs + 7 * 86400000;
      const sStartTs = parse(imp.shifted_earliest_start) || bStartTs;
      const sFinTs =
        parse(imp.shifted_earliest_finish) ||
        bFinTs + (imp.net_delay_days ?? 0) * 86400000;

      earliest = Math.min(earliest, bStartTs, sStartTs);
      latest = Math.max(latest, bFinTs, sFinTs);
    }

    if (earliest === Infinity) {
      earliest = Date.now();
      latest = earliest + 30 * 86400000;
    }

    const spanDays = Math.max(14, Math.ceil((latest - earliest) / (86400000)) + 4);

    // Add origin to items
    const origDur = Math.max(1, Math.round((origFinTs - origStartTs) / 86400000));
    items.push({
      id: data.activity_id,
      name: data.activity_name || data.activity_id,
      depth: 0,
      isOrigin: true,
      relationship: 'ORIGIN',
      baselineStart: origStart,
      baselineFinish: origFin,
      shiftedStart: origStart,
      shiftedFinish: origShiftFin,
      grossDelay: data.delay_days,
      netDelay: data.delay_days,
      absorbedDelay: 0,
      floatVal: 0,
      floatStatus: 'KNOWN',
      isCompleted: false,
      uncertainty: false,
      startOffsetDays: Math.max(0, Math.round((origStartTs - earliest) / 86400000)),
      plannedDurationDays: origDur,
      netShiftDays: data.delay_days,
    });

    for (const imp of data.impacts) {
      const bStartTs = parse(imp.original_earliest_start) || origFinTs;
      const bFinTs = parse(imp.original_planned_finish) || bStartTs + 7 * 86400000;
      const dur = Math.max(1, Math.round((bFinTs - bStartTs) / 86400000));
      const offset = Math.max(0, Math.round((bStartTs - earliest) / 86400000));

      items.push({
        id: imp.successor_activity_id,
        name: imp.activity_name || imp.successor_activity_id,
        depth: imp.propagation_depth || 1,
        isOrigin: false,
        relationship: imp.dependency_type || 'FS',
        baselineStart: imp.original_earliest_start,
        baselineFinish: imp.original_planned_finish,
        shiftedStart: imp.shifted_earliest_start,
        shiftedFinish: imp.shifted_earliest_finish,
        grossDelay: imp.gross_delay_days,
        netDelay: imp.net_delay_days ?? 0,
        absorbedDelay: imp.absorbed_delay_days ?? 0,
        floatVal: imp.total_float,
        floatStatus: imp.float_status,
        isCompleted: imp.execution_state === 'COMPLETED',
        uncertainty: imp.uncertainty,
        startOffsetDays: offset,
        plannedDurationDays: dur,
        netShiftDays: imp.net_delay_days ?? 0,
      });
    }

    return { timelineItems: items, minTimestamp: earliest, totalSpanDays: spanDays };
  }, [data]);

  return (
    <div className="space-y-4">
      {/* Legend & Guide */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 dark:bg-[#001438] rounded-xl border border-slate-200 dark:border-blue-900/40 text-[11px]">
        <div className="flex flex-wrap items-center gap-5">
          <div className="flex items-center gap-2">
            <span className="w-4 h-2.5 rounded bg-blue-500/80 dark:bg-blue-600/80 border border-blue-600" />
            <span className="text-slate-700 dark:text-slate-200 font-medium">Baseline Planned Duration</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-2.5 rounded bg-rose-500 dark:bg-rose-600 border border-rose-600" />
            <span className="text-rose-700 dark:text-rose-400 font-bold">Simulated Net Impacted Finish</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-2.5 rounded bg-emerald-500/40 border border-dashed border-emerald-600" />
            <span className="text-emerald-700 dark:text-emerald-400 font-medium">Absorbed by Float</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 font-mono text-[10px]">
          <Info className="w-3.5 h-3.5 text-blue-500" />
          Shift represents net schedule slip (A1 float absorption contract)
        </div>
      </div>

      {/* Gantt / Timeline Canvas */}
      <div className="bg-white dark:bg-[#001E60]/60 rounded-2xl border border-slate-200 dark:border-blue-900/50 p-4 shadow-sm overflow-x-auto">
        <div className="min-w-[800px] space-y-4">
          {timelineItems.map((item) => {
            const leftPct = (item.startOffsetDays / totalSpanDays) * 100;
            const baselineWidthPct = Math.max(3, (item.plannedDurationDays / totalSpanDays) * 100);
            const netShiftWidthPct = (item.netShiftDays / totalSpanDays) * 100;
            const absorbedWidthPct = (item.absorbedDelay / totalSpanDays) * 100;

            return (
              <div
                key={item.id}
                onClick={() => onSelectActivity?.(item.id)}
                className="group p-3 rounded-xl hover:bg-slate-50 dark:hover:bg-[#001438]/80 transition-colors border border-transparent hover:border-slate-200 dark:hover:border-blue-900/40 cursor-pointer"
              >
                {/* Row Header */}
                <div className="flex items-center justify-between gap-4 mb-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                      {item.id}
                    </span>
                    <span className="text-slate-400 dark:text-slate-500">·</span>
                    <span className="font-medium text-slate-700 dark:text-slate-300 text-[11px] truncate max-w-[280px]">
                      {item.name}
                    </span>
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                      {item.isOrigin ? 'ORIGIN' : `${item.relationship} · Hop ${item.depth}`}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 font-mono text-[11px]">
                    <span className="text-slate-500 dark:text-slate-400">
                      Plan: {item.baselineStart || 'TBD'} → {item.baselineFinish || 'TBD'}
                    </span>
                    {item.netDelay > 0 ? (
                      <span className="font-bold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 px-2 py-0.5 rounded border border-rose-200 dark:border-rose-500/30">
                        Shifted Finish: {item.shiftedFinish || `+${item.netDelay}d`} (+{item.netDelay}d net)
                      </span>
                    ) : item.absorbedDelay > 0 ? (
                      <span className="font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-500/30">
                        {item.absorbedDelay}d absorbed by float (0d net)
                      </span>
                    ) : (
                      <span className="text-slate-400">No shift</span>
                    )}
                  </div>
                </div>

                {/* Timeline Bar Track */}
                <div className="relative h-7 rounded-lg bg-slate-100 dark:bg-[#001438] w-full overflow-hidden flex items-center px-1">
                  {/* Baseline Bar */}
                  <div
                    className="absolute h-5 rounded bg-blue-500/80 dark:bg-blue-600/80 border border-blue-600 flex items-center justify-center text-[10px] text-white font-mono font-semibold truncate px-1 shadow-xs"
                    style={{
                      left: `${leftPct}%`,
                      width: `${baselineWidthPct}%`,
                    }}
                    title={`Baseline: ${item.baselineStart} to ${item.baselineFinish} (${item.plannedDurationDays}d)`}
                  >
                    {item.plannedDurationDays}d
                  </div>

                  {/* Absorbed Float Bar (if any) */}
                  {absorbedWidthPct > 0 && (
                    <div
                      className="absolute h-5 rounded bg-emerald-500/30 border border-dashed border-emerald-500 flex items-center justify-center text-[9px] text-emerald-800 dark:text-emerald-300 font-mono font-bold truncate px-0.5"
                      style={{
                        left: `${leftPct + baselineWidthPct}%`,
                        width: `${absorbedWidthPct}%`,
                      }}
                      title={`Float Absorbed: ${item.absorbedDelay} days`}
                    >
                      {item.absorbedDelay}d flt
                    </div>
                  )}

                  {/* Simulated Net Slip Bar (if any) */}
                  {netShiftWidthPct > 0 && (
                    <div
                      className="absolute h-5 rounded bg-rose-500 dark:bg-rose-600 border border-rose-600 flex items-center justify-center text-[9px] text-white font-mono font-bold truncate px-1 shadow-xs"
                      style={{
                        left: `${leftPct + baselineWidthPct + absorbedWidthPct}%`,
                        width: `${netShiftWidthPct}%`,
                      }}
                      title={`Net Impact: +${item.netDelay} days delay`}
                    >
                      +{item.netDelay}d
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
