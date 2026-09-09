import React, { useEffect, useState, useMemo } from 'react';
import {
  activitiesApi,
  auditApi,
  ActivityListItem,
  ActivityHistoryItem,
  AuditLogEntry,
} from '@/api';
import {
  Clock,
  Search,
  ShieldCheck,
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  AlertCircle,
  GitCommit,
  Hash,
  FileText,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Filter,
  Activity,
  Check,
  FileSpreadsheet,
  Mic,
  UploadCloud,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { cn } from '@/lib/utils';

// Status badge derived from authoritative approved progress
function ActivityStatusBadge({ status }: { status: string }) {
  const s = status?.toUpperCase() || '';
  if (s === 'COMPLETED') {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30 uppercase">
        <CheckCircle2 className="w-3 h-3" /> COMPLETED
      </span>
    );
  }
  if (s === 'IN PROGRESS') {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30 uppercase">
        <RotateCcw className="w-3 h-3 animate-spin-slow" /> IN PROGRESS
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 uppercase">
      <Clock className="w-3 h-3" /> NOT STARTED
    </span>
  );
}

function ClaimStatusBadge({ status }: { status: string }) {
  const s = status?.toUpperCase() || '';
  if (s === 'APPROVED') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30 uppercase">
        <CheckCircle2 className="w-3 h-3" /> {status}
      </span>
    );
  }
  if (s === 'REJECTED') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/30 uppercase">
        <XCircle className="w-3 h-3" /> {status}
      </span>
    );
  }
  if (s === 'REVIEW_REQUIRED' || s === 'HOLD' || s === 'FLAGGED') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30 uppercase">
        <RotateCcw className="w-3 h-3" /> {status}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-500/30 uppercase">
      {status}
    </span>
  );
}

function ChannelIcon({ channel }: { channel: string }) {
  const c = channel?.toUpperCase() || '';
  if (c.includes('VOICE')) return <Mic className="w-3.5 h-3.5 text-indigo-500" />;
  if (c.includes('FILE') || c.includes('DOCUMENT')) return <UploadCloud className="w-3.5 h-3.5 text-blue-500" />;
  if (c.includes('SCHEDULE') || c.includes('EXPORT')) return <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500" />;
  return <FileText className="w-3.5 h-3.5 text-amber-500" />;
}

const DISCIPLINES = [
  'ALL',
  'CIVIL',
  'PIPING',
  'ELECTRICAL',
  'INSTRUMENTATION',
  'STATIC_ROTATING_EQUIPMENT',
  'HSE',
];

export default function ActivityHistory() {
  // Navigation & selection state
  const [selectedActivityId, setSelectedActivityId] = useState<string | null>(null);

  // List view state
  const [activities, setActivities] = useState<ActivityListItem[]>([]);
  const [schedules, setSchedules] = useState<{ schedule_id: string; project_name: string; data_date?: string | null }[]>([]);
  const [selectedScheduleId, setSelectedScheduleId] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [selectedDiscipline, setSelectedDiscipline] = useState<string>('ALL');
  const [isListLoading, setIsListLoading] = useState<boolean>(true);
  const [listError, setListError] = useState<string | null>(null);

  // Detail view state
  const [detailActivity, setDetailActivity] = useState<ActivityListItem | null>(null);
  const [history, setHistory] = useState<ActivityHistoryItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Load activities list
  const loadActivities = async (schedId?: string, disc?: string) => {
    setIsListLoading(true);
    setListError(null);
    try {
      const res = await activitiesApi.list(schedId || undefined, disc || undefined);
      setActivities(res.activities);
      setSchedules(res.schedules);
      if (res.schedule_id && !selectedScheduleId) {
        setSelectedScheduleId(res.schedule_id);
      }
    } catch (e: any) {
      setListError('Failed to load schedule activities: ' + e.message);
    } finally {
      setIsListLoading(false);
    }
  };

  // Load detail for selected activity
  const loadActivityDetail = async (actId: string) => {
    setIsDetailLoading(true);
    setDetailError(null);
    try {
      const [histData, logs] = await Promise.all([
        activitiesApi.getHistory(actId),
        auditApi.getLogs(),
      ]);
      setDetailActivity(histData.activity);
      setHistory(histData.history);

      // Filter audit logs to this activity or linked events if possible
      const linkedEventIds = new Set(histData.history.map((h) => h.event_id));
      const relevantLogs = logs.filter(
        (log) => log.entity_id === actId || linkedEventIds.has(log.entity_id)
      );
      setAuditLogs(relevantLogs.length > 0 ? relevantLogs : logs.slice(0, 10));
    } catch (e: any) {
      setDetailError('Failed to fetch activity history: ' + e.message);
    } finally {
      setIsDetailLoading(false);
    }
  };

  useEffect(() => {
    loadActivities(selectedScheduleId || undefined, selectedDiscipline !== 'ALL' ? selectedDiscipline : undefined);
  }, [selectedScheduleId, selectedDiscipline]);

  useEffect(() => {
    if (selectedActivityId) {
      loadActivityDetail(selectedActivityId);
    } else {
      setDetailActivity(null);
      setHistory([]);
    }
  }, [selectedActivityId]);

  // Client-side search across activity ID, activity name, location, WBS
  const filteredActivities = useMemo(() => {
    if (!searchFilter.trim()) return activities;
    const q = searchFilter.trim().toLowerCase();
    return activities.filter(
      (act) =>
        act.activity_id.toLowerCase().includes(q) ||
        act.activity_name.toLowerCase().includes(q) ||
        act.location.toLowerCase().includes(q) ||
        (act.wbs_code && act.wbs_code.toLowerCase().includes(q))
    );
  }, [activities, searchFilter]);

  // Summary counts
  const stats = useMemo(() => {
    let completed = 0;
    let inProgress = 0;
    let notStarted = 0;
    for (const act of activities) {
      if (act.approved_pct >= 100) completed++;
      else if (act.approved_pct > 0) inProgress++;
      else notStarted++;
    }
    return { total: activities.length, completed, inProgress, notStarted };
  }, [activities]);

  return (
    <div className="space-y-6">
      {/* ─── Top Header ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            {selectedActivityId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedActivityId(null)}
                className="h-8 px-2 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 mr-1"
              >
                <ArrowLeft className="w-4 h-4 mr-1" /> Back to List
              </Button>
            )}
            <div className="p-1.5 rounded-lg bg-[#E31E24]/10 border border-[#E31E24]/20">
              <Clock className="w-5 h-5 text-[#E31E24]" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              {selectedActivityId ? 'Activity Detail & Report Traceability' : 'Activity History & Progress Tracking'}
            </h1>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">
            {selectedActivityId
              ? `Inspection and complete verification trail for ${selectedActivityId}`
              : 'Primavera / P6 baseline schedule activities with authoritative approved actuals'}
          </p>
        </div>

        {/* Schedule Selector if multiple schedules exist */}
        {schedules.length > 1 && !selectedActivityId && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 dark:text-slate-400 font-medium">Schedule:</span>
            <select
              value={selectedScheduleId || ''}
              onChange={(e) => setSelectedScheduleId(e.target.value)}
              className="bg-white dark:bg-[#1c1a19] border border-slate-300 dark:border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100 font-mono focus:border-[#E31E24] focus:outline-none"
            >
              {schedules.map((s) => (
                <option key={s.schedule_id} value={s.schedule_id}>
                  {s.project_name || s.schedule_id}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* ─── VIEW 1: Activity List (when no activity is selected) ──────────────── */}
      {!selectedActivityId && (
        <div className="space-y-6">
          {/* Progress Metric Summary Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-4 rounded-xl bg-white dark:bg-[#262322]/80 border border-slate-200 dark:border-white/10 shadow-sm">
              <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                Total Activities
              </span>
              <span className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100 mt-1 block">
                {stats.total}
              </span>
            </div>
            <div className="p-4 rounded-xl bg-white dark:bg-[#262322]/80 border border-slate-200 dark:border-white/10 shadow-sm">
              <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                Not Started (0%)
              </span>
              <span className="text-2xl font-bold font-mono text-slate-600 dark:text-slate-400 mt-1 block">
                {stats.notStarted}
              </span>
            </div>
            <div className="p-4 rounded-xl bg-white dark:bg-[#262322]/80 border border-slate-200 dark:border-white/10 shadow-sm">
              <span className="text-[10px] font-bold text-amber-500 uppercase tracking-wider block">
                In Progress (1-99%)
              </span>
              <span className="text-2xl font-bold font-mono text-amber-600 dark:text-amber-400 mt-1 block">
                {stats.inProgress}
              </span>
            </div>
            <div className="p-4 rounded-xl bg-white dark:bg-[#262322]/80 border border-slate-200 dark:border-white/10 shadow-sm">
              <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-wider block">
                Completed (100%)
              </span>
              <span className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-1 block">
                {stats.completed}
              </span>
            </div>
          </div>

          {/* Search & Discipline Filter Bar */}
          <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <Input
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Search by Activity ID, Name, or Location..."
                className="pl-9 bg-white dark:bg-[#1c1a19] border-slate-300 dark:border-white/10 text-slate-900 dark:text-slate-100 text-xs h-9 focus:border-[#E31E24]"
              />
            </div>

            {/* Discipline Pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0 mr-1" />
              {DISCIPLINES.map((disc) => (
                <button
                  key={disc}
                  onClick={() => setSelectedDiscipline(disc)}
                  className={cn(
                    'text-[10px] font-mono px-2.5 py-1 rounded-lg transition-colors shrink-0 font-medium',
                    selectedDiscipline === disc
                      ? 'bg-[#E31E24] text-white shadow-sm'
                      : 'bg-white dark:bg-[#262322]/80 border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                  )}
                >
                  {disc === 'STATIC_ROTATING_EQUIPMENT' ? 'EQUIPMENT' : disc}
                </button>
              ))}
            </div>
          </div>

          {/* List Content */}
          {isListLoading ? (
            <div className="space-y-3">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-24 bg-slate-100 dark:bg-[#262322]/50 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : listError ? (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              {listError}
            </div>
          ) : filteredActivities.length === 0 ? (
            <div className="text-center py-16 bg-white dark:bg-[#262322]/60 border border-slate-200 dark:border-white/10 rounded-2xl text-slate-400 dark:text-slate-500 text-xs">
              <Activity className="w-8 h-8 mx-auto mb-2 opacity-30" />
              No schedule activities found matching your criteria.
            </div>
          ) : (
            <div className="space-y-3">
              {filteredActivities.map((act) => {
                const approvedPct = act.approved_pct ?? 0;
                return (
                  <div
                    key={act.activity_id}
                    onClick={() => setSelectedActivityId(act.activity_id)}
                    className="p-4 rounded-xl bg-white dark:bg-[#262322]/80 border border-slate-200 dark:border-white/10 hover:border-[#E31E24]/50 shadow-sm hover:shadow transition-all cursor-pointer group"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      {/* Left: Metadata & Name */}
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="bg-slate-900 dark:bg-slate-800 text-white font-mono text-xs px-2.5 py-0.5 rounded-md font-bold tracking-tight">
                            {act.activity_id}
                          </span>
                          <span className="text-[10px] bg-slate-100 dark:bg-blue-900/60 text-slate-700 dark:text-blue-200 border border-slate-200 dark:border-white/10 px-2 py-0.5 rounded-full font-mono uppercase">
                            {act.discipline}
                          </span>
                          {act.wbs_code && (
                            <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                              WBS: {act.wbs_code}
                            </span>
                          )}
                          <ActivityStatusBadge status={act.status} />
                        </div>

                        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate group-hover:text-[#E31E24] transition-colors">
                          {act.activity_name}
                        </h3>

                        <div className="flex items-center gap-4 text-[11px] text-slate-500 dark:text-slate-400 flex-wrap">
                          <span>Location: <strong className="text-slate-700 dark:text-slate-300">{act.location}</strong></span>
                          <span>Window: <span className="font-mono text-slate-600 dark:text-slate-400">{act.planned_start}</span> to <span className="font-mono text-slate-600 dark:text-slate-400">{act.planned_finish}</span></span>
                          {act.planned_quantity !== null && (
                            <span>Planned Qty: <strong className="font-mono text-slate-700 dark:text-slate-300">{act.planned_quantity} {act.uom || ''}</strong></span>
                          )}
                        </div>
                      </div>

                      {/* Right: Authoritative Approved Progress */}
                      <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center border-t sm:border-t-0 sm:border-l border-slate-100 dark:border-white/10 pt-2 sm:pt-0 sm:pl-6 shrink-0 min-w-[160px]">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-slate-400 dark:text-slate-500 uppercase font-mono">Approved:</span>
                          <span className={cn(
                            'text-lg font-bold font-mono',
                            approvedPct >= 100 ? 'text-emerald-600 dark:text-emerald-400' : approvedPct > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400 dark:text-slate-500'
                          )}>
                            {approvedPct}%
                          </span>
                        </div>

                        {/* Progress bar */}
                        <div className="w-28 sm:w-36 h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden mt-1.5">
                          <div
                            className={cn(
                              'h-full transition-all duration-300',
                              approvedPct >= 100 ? 'bg-emerald-500' : approvedPct > 0 ? 'bg-amber-500' : 'bg-slate-300 dark:bg-slate-700'
                            )}
                            style={{ width: `${Math.min(100, Math.max(0, approvedPct))}%` }}
                          />
                        </div>

                        <span className="text-[10px] text-[#E31E24] font-medium flex items-center gap-0.5 mt-1 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                          View History <ChevronRight className="w-3 h-3" />
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ─── VIEW 2: Activity Detail & Chronological Report History ────────────── */}
      {selectedActivityId && (
        <div className="space-y-6">
          {isDetailLoading ? (
            <div className="space-y-4">
              <div className="h-32 bg-slate-100 dark:bg-[#262322]/50 rounded-2xl animate-pulse" />
              <div className="h-64 bg-slate-100 dark:bg-[#262322]/50 rounded-2xl animate-pulse" />
            </div>
          ) : detailError ? (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              {detailError}
            </div>
          ) : (
            <>
              {/* Activity Metadata Header Card */}
              {detailActivity && (
                <Card className="bg-white dark:bg-[#262322]/80 border-slate-200 dark:border-white/10 shadow-sm">
                  <CardContent className="p-4 sm:p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="bg-[#262322] dark:bg-[#E31E24] text-white font-mono text-xs px-2.5 py-0.5 rounded-md font-bold">
                          {detailActivity.activity_id}
                        </span>
                        <span className="text-xs bg-slate-100 dark:bg-blue-900/80 text-slate-700 dark:text-blue-200 border border-slate-200 dark:border-white/10 px-2 py-0.5 rounded-full font-mono uppercase">
                          {detailActivity.discipline}
                        </span>
                        {detailActivity.wbs_code && (
                          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                            WBS: {detailActivity.wbs_code}
                          </span>
                        )}
                        {detailActivity.asset_tag && (
                          <span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono px-2 py-0.5 rounded-md">
                            Tag: {detailActivity.asset_tag}
                          </span>
                        )}
                        <ActivityStatusBadge status={detailActivity.status} />
                      </div>

                      <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                        {detailActivity.activity_name}
                      </h2>

                      <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400 flex-wrap">
                        <span>Location: <strong className="text-slate-700 dark:text-slate-200">{detailActivity.location}</strong></span>
                        <span>Planned Window: <span className="font-mono text-slate-700 dark:text-slate-300">{detailActivity.planned_start}</span> to <span className="font-mono text-slate-700 dark:text-slate-300">{detailActivity.planned_finish}</span></span>
                      </div>
                    </div>

                    {/* Right: Progress Comparison Card */}
                    <div className="flex gap-6 border-t md:border-t-0 md:border-l border-slate-200 dark:border-white/10 pt-4 md:pt-0 md:pl-6 text-xs font-mono shrink-0">
                      <div>
                        <span className="text-[10px] uppercase text-slate-400 dark:text-slate-500 block mb-0.5">
                          Baseline Planned
                        </span>
                        <span className="text-slate-600 dark:text-slate-400 font-bold text-lg">
                          {detailActivity.baseline_pct_complete}<span className="text-sm text-slate-400">%</span>
                        </span>
                      </div>

                      <div>
                        <span className="text-[10px] uppercase text-slate-400 dark:text-slate-500 block mb-0.5">
                          Approved Actual
                        </span>
                        <span className={cn(
                          'font-bold text-2xl',
                          detailActivity.approved_pct >= 100 ? 'text-emerald-600 dark:text-emerald-400' : detailActivity.approved_pct > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400'
                        )}>
                          {detailActivity.approved_pct}<span className="text-sm font-normal">%</span>
                        </span>
                      </div>

                      {detailActivity.planned_quantity !== null && (
                        <div>
                          <span className="text-[10px] uppercase text-slate-400 dark:text-slate-500 block mb-0.5">
                            Planned Qty
                          </span>
                          <span className="text-slate-900 dark:text-slate-100 font-bold text-lg">
                            {detailActivity.planned_quantity} <span className="text-xs text-slate-400">{detailActivity.uom || ''}</span>
                          </span>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Traceability Flow Banner */}
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-white/5 text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between overflow-x-auto gap-3">
                <span className="font-semibold text-slate-700 dark:text-slate-300 shrink-0">
                  Verification Pipeline:
                </span>
                <div className="flex items-center gap-2 shrink-0 font-mono text-[10px]">
                  <span className="px-2 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">1. Field Report</span>
                  <ArrowRight className="w-3 h-3 text-slate-400" />
                  <span className="px-2 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">2. AI Matching</span>
                  <ArrowRight className="w-3 h-3 text-slate-400" />
                  <span className="px-2 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">3. Checks & Flags</span>
                  <ArrowRight className="w-3 h-3 text-slate-400" />
                  <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 font-bold">4. Supervisor Decision</span>
                  <ArrowRight className="w-3 h-3 text-slate-400" />
                  <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-bold">5. Approved Actual</span>
                </div>
              </div>

              {/* Chronological Claim & Decision History */}
              <Card className="bg-white dark:bg-[#262322]/80 border-slate-200 dark:border-white/10 shadow-sm">
                <CardHeader className="pb-3 border-b border-slate-200 dark:border-white/10">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <CalendarDays className="w-4 h-4 text-[#E31E24]" />
                      Chronological Claim & Decision History ({history.length} {history.length === 1 ? 'event' : 'events'})
                    </CardTitle>
                    <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500">
                      Authoritative current progress: <strong className="text-slate-900 dark:text-slate-100">{detailActivity?.approved_pct ?? 0}%</strong>
                    </span>
                  </div>
                  <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
                    All field claims, AI matches, and Supervisor decisions mapped to this activity in chronological sequence.
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-6">
                  {history.length === 0 ? (
                    <div className="text-center py-12 text-slate-400 dark:text-slate-500 text-xs space-y-2">
                      <GitCommit className="w-8 h-8 mx-auto opacity-30" />
                      <p className="font-medium text-slate-600 dark:text-slate-400">No field claims or reports have been submitted for this activity yet.</p>
                      <p className="text-[11px]">Official progress remains at 0% (NOT STARTED) until a report is submitted and approved by a Supervisor.</p>
                    </div>
                  ) : (
                    <div className="relative pl-6 border-l-2 border-slate-200 dark:border-white/10 space-y-6">
                      {history.map((item, idx) => (
                        <div key={item.event_id || idx} className="relative group">
                          {/* Timeline Dot */}
                          <div
                            className={cn(
                              'absolute -left-[31px] top-2 w-3.5 h-3.5 rounded-full border-4 border-white dark:border-[#262322] shadow transition-transform group-hover:scale-125',
                              item.supervisor_action === 'APPROVE'
                                ? 'bg-emerald-500'
                                : item.supervisor_action === 'REJECT'
                                ? 'bg-rose-500'
                                : item.supervisor_action === 'EDIT'
                                ? 'bg-amber-500'
                                : 'bg-[#E31E24]'
                            )}
                          />

                          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-700 hover:border-[#E31E24]/40 transition-colors space-y-3 text-xs">
                            {/* Header: Event ID, Channel, Status, Timestamp */}
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-mono font-bold text-slate-900 dark:text-slate-200">
                                  {item.event_id}
                                </span>
                                <span className="inline-flex items-center gap-1 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[10px] font-mono px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700">
                                  <ChannelIcon channel={item.input_channel} />
                                  {item.input_channel}
                                </span>
                                <ClaimStatusBadge status={item.status} />
                              </div>

                              <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500 flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {item.timestamp ? new Date(item.timestamp).toLocaleString() : item.event_date}
                              </span>
                            </div>

                            {/* Raw Claim Text */}
                            <div className="p-3 rounded-lg bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-700/80">
                              <p className="text-slate-800 dark:text-slate-200 font-medium leading-relaxed italic">
                                "{item.raw_claim_text}"
                              </p>
                            </div>

                            {/* Traceability Row: Claimed vs Mapped */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 text-[11px] bg-slate-100/60 dark:bg-slate-900/40 p-2.5 rounded-lg border border-slate-200/60 dark:border-slate-800">
                              <div>
                                <span className="text-slate-400 dark:text-slate-500 block text-[10px] uppercase font-mono">Claimed Progress:</span>
                                <span className="font-bold text-slate-800 dark:text-slate-200 font-mono">
                                  {item.claimed_pct !== null ? `${item.claimed_pct}%` : item.claimed_qty !== null ? `${item.claimed_qty} ${item.claimed_uom || ''}` : 'N/A'}
                                </span>
                              </div>

                              <div>
                                <span className="text-slate-400 dark:text-slate-500 block text-[10px] uppercase font-mono">Mapped Activity:</span>
                                <span className="font-mono text-slate-700 dark:text-slate-300 font-medium">
                                  {item.matched_activity_id || item.reported_activity_id || selectedActivityId}
                                </span>
                              </div>

                              {item.delay_reason && (
                                <div>
                                  <span className="text-rose-400 dark:text-rose-500 block text-[10px] uppercase font-mono">Delay Reason:</span>
                                  <span className="font-medium text-rose-600 dark:text-rose-400 font-mono">
                                    {item.delay_reason}
                                  </span>
                                </div>
                              )}
                            </div>

                            {/* Supervisor Decision Block */}
                            {item.supervisor_action ? (
                              <div className="p-3 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-500/30 space-y-1.5">
                                <div className="flex items-center justify-between flex-wrap gap-2">
                                  <span className="font-bold text-[11px] text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
                                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                                    Supervisor Decision: <strong className="uppercase">{item.supervisor_action}</strong>
                                  </span>
                                  {item.approved_pct !== null && (
                                    <span className="text-[11px] font-mono font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-900/60 px-2 py-0.5 rounded">
                                      Official Progress: {item.approved_pct}%
                                    </span>
                                  )}
                                </div>
                                {item.justification && (
                                  <p className="text-[11px] text-emerald-900 dark:text-emerald-200 leading-normal">
                                    <strong>Justification:</strong> {item.justification}
                                  </p>
                                )}
                              </div>
                            ) : (
                              <div className="p-2.5 rounded-lg bg-amber-50/70 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-500/30 text-[11px] text-amber-800 dark:text-amber-300 flex items-center gap-2">
                                <RotateCcw className="w-3.5 h-3.5 shrink-0 text-amber-600" />
                                <span>No Supervisor decision has been recorded yet. Claimed value is unapproved.</span>
                              </div>
                            )}

                            {/* Source References / Evidence */}
                            {item.source_references && item.source_references.length > 0 && (
                              <div className="space-y-1 pt-1">
                                <span className="text-[10px] uppercase font-mono text-slate-400 dark:text-slate-500">
                                  Source Evidence References:
                                </span>
                                <div className="flex flex-wrap gap-2">
                                  {item.source_references.map((ref) => (
                                    <span
                                      key={ref.reference_id}
                                      className="inline-flex items-center gap-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 text-[10px] font-mono px-2 py-0.5 rounded"
                                    >
                                      <FileText className="w-3 h-3 text-slate-400" />
                                      {ref.file_name || ref.reference_id}
                                      {ref.sheet_name && ` (${ref.sheet_name})`}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Cryptographic Audit Trail */}
              <Card className="bg-white dark:bg-[#262322]/80 border-slate-200 dark:border-white/10 shadow-sm">
                <CardHeader className="pb-3 border-b border-slate-200 dark:border-white/10">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <span className="text-slate-900 dark:text-slate-200">Cryptographic Audit Trail</span>
                    <span className="text-[10px] bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 px-2 py-0.5 rounded-full font-mono">
                      SHA-256 Hash Chain
                    </span>
                  </CardTitle>
                  <CardDescription className="text-slate-500 dark:text-slate-400 text-xs">
                    Tamper-evident log guaranteeing non-repudiation of field claims and planner decisions for this activity.
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-4 space-y-3 font-mono text-[11px]">
                  {auditLogs.length === 0 ? (
                    <div className="text-center py-6 text-slate-400 dark:text-slate-500">
                      No audit log entries found.
                    </div>
                  ) : (
                    auditLogs.map((log) => (
                      <div
                        key={log.log_id}
                        className="p-3 bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-700 rounded-xl space-y-2 hover:border-emerald-300 dark:hover:border-emerald-700/50 transition-colors"
                      >
                        <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 flex-wrap gap-1">
                          <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                            <Hash className="w-3 h-3 text-emerald-500" />
                            LOG {log.log_id} · {log.action}
                          </span>
                          <span className="text-slate-400 dark:text-slate-500 text-[10px]">
                            {new Date(log.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px]">
                          <div className="truncate p-2 bg-slate-100 dark:bg-slate-900/60 rounded-lg">
                            <span className="text-slate-400 dark:text-slate-500 block mb-0.5">Prev Hash:</span>
                            <span className="text-slate-500 dark:text-slate-500">{log.previous_hash}</span>
                          </div>
                          <div className="truncate p-2 bg-slate-100 dark:bg-slate-900/60 rounded-lg">
                            <span className="text-slate-400 dark:text-slate-500 block mb-0.5">Curr Hash:</span>
                            <span className="text-[#E31E24] dark:text-sky-400">{log.current_hash}</span>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  );
}

