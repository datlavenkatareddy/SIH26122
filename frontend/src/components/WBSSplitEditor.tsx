import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Layers,
  Loader2,
  RotateCcw,
  Save,
} from 'lucide-react';
import { ExecutionEvent, ScheduleActivity, SplitBasis, claimsApi, wbsApi } from '../api';

// Feature 30 (M5 half): the Supervisor edits the persisted WBS split of a broad claim.
// The backend decomposes the claim across eligible sibling activities (completed and
// future siblings get 0); this editor only adjusts each row's share. Shares are entered
// as percentages here and sent to the API as fractions that must sum to 1.0.

interface WBSSplitEditorProps {
  claim: ExecutionEvent;
  activities: ScheduleActivity[];
  onSuccess: () => void;
  onCancel: () => void;
}

interface Row {
  activity_id: string;
  split_basis: SplitBasis;
  pct: number; // 0-100
  original_pct: number;
  rationale: string;
}

const BASIS_STYLE: Record<string, string> = {
  EQUAL: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  WBS_WEIGHTED: 'bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300',
  MANUAL: 'bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300',
};

export const WBSSplitEditor: React.FC<WBSSplitEditorProps> = ({
  claim,
  activities,
  onSuccess,
  onCancel,
}) => {
  const isPctMode = claim.claim_mode === 'CUMULATIVE_PCT';
  const claimValue = isPctMode ? claim.claimed_pct : claim.claimed_quantity;
  const unit = isPctMode ? '%' : claim.claimed_uom || 'units';

  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const splits = await wbsApi.getSplits(claim.event_id);
      setRows(
        splits.map((s) => ({
          activity_id: s.activity_id,
          split_basis: s.split_basis,
          pct: Number((s.split_pct * 100).toFixed(2)),
          original_pct: Number((s.split_pct * 100).toFixed(2)),
          rationale: s.rationale || '',
        }))
      );
    } catch (err: any) {
      setError(err?.message || 'Failed to load the WBS split.');
    } finally {
      setLoading(false);
    }
  }, [claim.event_id]);

  useEffect(() => {
    load();
  }, [load]);

  const total = useMemo(() => rows.reduce((sum, r) => sum + (Number(r.pct) || 0), 0), [rows]);
  const isBalanced = Math.abs(total - 100) <= 0.01;
  const dirty = rows.some((r) => Math.abs(r.pct - r.original_pct) > 1e-9);

  const nameOf = (id: string) => activities.find((a) => a.activity_id === id)?.activity_name || '';

  const handleSave = async () => {
    if (!isBalanced) {
      setError(`Shares must sum to 100% (currently ${total.toFixed(2)}%).`);
      return;
    }
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await wbsApi.updateSplits(
        claim.event_id,
        rows.map((r) => ({ activity_id: r.activity_id, split_pct: r.pct / 100 }))
      );
      // Splits changed -> per-child validation, sequence checks and priority must be recomputed.
      await claimsApi.check(claim.event_id);
      setSaved(true);
      onSuccess();
    } catch (err: any) {
      setError(err?.message || 'Failed to save the WBS split.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-[#1565C0] dark:text-blue-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              WBS Split Allocation
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-300">
                Granularity Bridge
              </span>
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              This broad claim was decomposed across sibling activities. Completed and not-yet-eligible
              siblings receive nothing; adjust the shares if the field reality differs.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading || saving}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg text-foreground bg-card-subtle hover:bg-muted border border-border transition-colors"
          title="Discard edits and reload the suggested split"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset
        </button>
      </div>

      <div className="mt-4 p-3 rounded-lg bg-card-subtle border border-border flex flex-wrap items-center justify-between gap-3 text-xs">
        <div>
          <span className="text-muted-foreground">Claim: </span>
          <span className="font-mono font-semibold text-foreground">{claim.event_id.slice(0, 8)}</span>
          <span className="mx-2 text-border">•</span>
          <span className="text-muted-foreground">Mode: </span>
          <span className="font-medium text-foreground">
            {isPctMode ? 'Cumulative Percentage' : 'Incremental Quantity'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Claim value:</span>
          <span className="font-bold text-sm text-[#FF7A18]">
            {claimValue ?? '—'} {unit}
          </span>
        </div>
      </div>

      {loading ? (
        <div className="mt-6 flex items-center justify-center text-xs text-muted-foreground gap-2">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading split…
        </div>
      ) : rows.length === 0 ? (
        <p className="mt-4 text-xs text-muted-foreground">This claim was matched to a single activity; there is no split to edit.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {rows.map((row, idx) => {
            const contribution = claimValue != null ? (claimValue * row.pct) / 100 : null;
            const changed = Math.abs(row.pct - row.original_pct) > 1e-9;
            return (
              <div
                key={row.activity_id}
                className="p-3.5 rounded-lg border border-border bg-card-subtle hover:border-primary/50 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-bold text-sm text-foreground">{row.activity_id}</span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded font-mono ${
                          BASIS_STYLE[changed ? 'MANUAL' : row.split_basis] || BASIS_STYLE.EQUAL
                        }`}
                      >
                        {changed ? 'MANUAL' : row.split_basis}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate">{nameOf(row.activity_id)}</p>
                    {row.rationale && (
                      <p className="text-[10px] text-muted-foreground/80 mt-0.5">{row.rationale}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      aria-label={`Share for ${row.activity_id}`}
                      min={0}
                      max={100}
                      step={0.01}
                      value={row.pct}
                      onChange={(e) => {
                        const v = e.target.value === '' ? 0 : Number(e.target.value);
                        setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, pct: v } : r)));
                        setSaved(false);
                      }}
                      className="w-20 px-2 py-1.5 text-right rounded-md border border-border bg-card text-foreground font-mono text-xs"
                    />
                    <span className="text-xs text-muted-foreground">%</span>
                    <span className="w-28 text-right text-[11px] font-mono text-foreground">
                      {contribution != null ? `${contribution.toFixed(2)} ${unit}` : '—'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}

          <div
            className={`flex items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold border ${
              isBalanced
                ? 'bg-status-approved/10 border-status-approved/30 text-status-approved'
                : 'bg-status-warning/10 border-status-warning/30 text-status-warning'
            }`}
          >
            <span className="flex items-center gap-1.5">
              {isBalanced ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
              Total {total.toFixed(2)}%
            </span>
            <span>{isBalanced ? 'Balanced' : 'Must equal 100%'}</span>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-3 text-xs rounded-lg border border-destructive/30 bg-destructive/10 text-destructive px-3 py-2">
          {error}
        </div>
      )}
      {saved && !error && (
        <div className="mt-3 text-xs rounded-lg border border-status-approved/30 bg-status-approved/10 text-status-approved px-3 py-2">
          Split saved and claim re-checked.
        </div>
      )}

      <div className="mt-4 flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border text-foreground bg-card-subtle hover:bg-muted transition-colors"
        >
          Back to candidates
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || loading || rows.length === 0 || !dirty || !isBalanced}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-gradient-to-r from-[#FF7A18] to-[#FF941F] text-white disabled:opacity-50"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          Save split
        </button>
      </div>
    </div>
  );
};
