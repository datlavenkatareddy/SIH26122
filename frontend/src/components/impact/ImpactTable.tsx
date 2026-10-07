import React, { useState, useMemo } from 'react';
import { ImpactPreviewResult, ImpactEvaluationItem } from '@/api';
import {
  Search,
  Filter,
  ArrowUpDown,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

interface ImpactTableProps {
  data: ImpactPreviewResult;
  selectedActivityId: string | null;
  onSelectActivity: (id: string) => void;
}

type SortField =
  | 'successor_activity_id'
  | 'dependency_type'
  | 'gross_delay_days'
  | 'total_float'
  | 'net_delay_days'
  | 'propagation_depth'
  | 'execution_state'
  | 'uncertainty';

export function ImpactTable({ data, selectedActivityId, onSelectActivity }: ImpactTableProps) {
  const [search, setSearch] = useState('');
  const [depthFilter, setDepthFilter] = useState<string>('ALL');
  const [stateFilter, setStateFilter] = useState<string>('ALL');
  const [sortField, setSortField] = useState<SortField>('propagation_depth');
  const [sortAsc, setSortAsc] = useState(true);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const filteredAndSortedImpacts = useMemo(() => {
    return data.impacts
      .filter((imp) => {
        if (search.trim()) {
          const q = search.toLowerCase();
          const matchId = imp.successor_activity_id.toLowerCase().includes(q);
          const matchName = (imp.activity_name || '').toLowerCase().includes(q);
          const matchPred = (imp.controlling_predecessor || '').toLowerCase().includes(q);
          if (!matchId && !matchName && !matchPred) return false;
        }
        if (depthFilter !== 'ALL' && imp.propagation_depth !== Number(depthFilter)) {
          return false;
        }
        if (stateFilter !== 'ALL' && imp.execution_state !== stateFilter) {
          return false;
        }
        return true;
      })
      .sort((a, b) => {
        let valA: any = a[sortField];
        let valB: any = b[sortField];

        if (valA === null || valA === undefined) valA = sortAsc ? Infinity : -Infinity;
        if (valB === null || valB === undefined) valB = sortAsc ? Infinity : -Infinity;

        if (typeof valA === 'string') {
          return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return sortAsc ? valA - valB : valB - valA;
      });
  }, [data.impacts, search, depthFilter, stateFilter, sortField, sortAsc]);

  return (
    <div className="space-y-4">
      {/* Search & Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 bg-slate-50 dark:bg-[#001438] rounded-xl border border-slate-200 dark:border-blue-900/40 text-xs">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search activity ID, name, or predecessor..."
            className="pl-9 bg-white dark:bg-[#001E60] border-slate-300 dark:border-blue-800 text-xs h-9 font-mono"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-slate-500 text-xs">
            <Filter className="w-3.5 h-3.5" />
            <span>Depth:</span>
            <select
              value={depthFilter}
              onChange={(e) => setDepthFilter(e.target.value)}
              className="bg-white dark:bg-[#001E60] border border-slate-300 dark:border-blue-800 rounded-md px-2 py-1 text-xs font-mono"
            >
              <option value="ALL">All Depths</option>
              <option value="1">Hop 1 (Direct)</option>
              <option value="2">Hop 2</option>
              <option value="3">Hop 3+</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-slate-500 text-xs">
            <span>State:</span>
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="bg-white dark:bg-[#001E60] border border-slate-300 dark:border-blue-800 rounded-md px-2 py-1 text-xs font-mono"
            >
              <option value="ALL">All States</option>
              <option value="NOT_STARTED">Not Started</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COMPLETED">Completed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Enterprise Data Table */}
      <div className="bg-white dark:bg-[#001E60]/60 rounded-2xl border border-slate-200 dark:border-blue-900/50 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-blue-900/50 bg-slate-50/75 dark:bg-[#001438]/80 text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <th
                  onClick={() => handleSort('successor_activity_id')}
                  className="py-3 px-4 cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center gap-1">
                    <span>Activity</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('dependency_type')}
                  className="py-3 px-3 cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center gap-1">
                    <span>Relationship</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('gross_delay_days')}
                  className="py-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Gross Delay</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('total_float')}
                  className="py-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Float</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('net_delay_days')}
                  className="py-3 px-3 text-right cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center justify-end gap-1">
                    <span>Net Impact</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('propagation_depth')}
                  className="py-3 px-3 text-center cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center justify-center gap-1">
                    <span>Depth</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('execution_state')}
                  className="py-3 px-3 cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center gap-1">
                    <span>State</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('uncertainty')}
                  className="py-3 px-4 cursor-pointer hover:text-slate-900 dark:hover:text-slate-200"
                >
                  <div className="flex items-center gap-1">
                    <span>Uncertainty</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-blue-900/30">
              {filteredAndSortedImpacts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400 text-xs">
                    No downstream impacted activities found matching your filters.
                  </td>
                </tr>
              ) : (
                filteredAndSortedImpacts.map((imp) => {
                  const isSelected = selectedActivityId === imp.successor_activity_id;
                  const isSlip = imp.net_delay_days && imp.net_delay_days > 0;
                  const isAbsorbed =
                    imp.gross_delay_days > 0 && (!imp.net_delay_days || imp.net_delay_days === 0);

                  return (
                    <tr
                      key={imp.successor_activity_id}
                      onClick={() => onSelectActivity(imp.successor_activity_id)}
                      className={cn(
                        'hover:bg-slate-50 dark:hover:bg-[#001438]/60 cursor-pointer transition-colors',
                        isSelected && 'bg-violet-50/70 dark:bg-violet-950/30 font-medium'
                      )}
                    >
                      <td className="py-3 px-4">
                        <div className="font-mono font-bold text-slate-900 dark:text-slate-100">
                          {imp.successor_activity_id}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1 max-w-[240px]">
                          {imp.activity_name}
                        </div>
                      </td>

                      <td className="py-3 px-3 font-mono">
                        <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-[10px] font-semibold">
                          {imp.dependency_type}
                        </span>
                        {imp.controlling_predecessor && (
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            via {imp.controlling_predecessor}
                          </div>
                        )}
                      </td>

                      <td className="py-3 px-3 text-right font-mono text-slate-700 dark:text-slate-300">
                        +{imp.gross_delay_days}d
                      </td>

                      <td className="py-3 px-3 text-right font-mono">
                        {imp.float_status === 'KNOWN' && imp.total_float !== null ? (
                          <span className="text-slate-600 dark:text-slate-400">
                            {imp.total_float}d
                          </span>
                        ) : (
                          <span className="text-amber-600 dark:text-amber-400 text-[10px]">
                            UNKNOWN
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-3 text-right font-mono font-bold">
                        {isSlip ? (
                          <span className="text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 px-2 py-0.5 rounded">
                            +{imp.net_delay_days}d
                          </span>
                        ) : isAbsorbed ? (
                          <span className="text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-2 py-0.5 rounded text-[11px]">
                            0d (Absorbed)
                          </span>
                        ) : (
                          <span className="text-slate-400">0d</span>
                        )}
                      </td>

                      <td className="py-3 px-3 text-center font-mono">
                        <span className="px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[10px] font-semibold">
                          Hop {imp.propagation_depth}
                        </span>
                      </td>

                      <td className="py-3 px-3 font-mono text-[10px]">
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded-full font-semibold',
                            imp.execution_state === 'COMPLETED'
                              ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                              : imp.execution_state === 'IN_PROGRESS'
                              ? 'bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300'
                              : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                          )}
                        >
                          {imp.execution_state}
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        {imp.uncertainty ? (
                          <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-semibold text-[10px]">
                            <AlertTriangle className="w-3 h-3" /> Yes
                          </span>
                        ) : (
                          <span className="text-slate-400 text-[10px]">Deterministic</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
