import React, { useEffect, useState } from 'react';
import {
  HelpCircle,
  Sparkles,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  Network,
  FileCheck2,
  GitBranch,
  X,
  Send,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { AskWhyResponse, AskWhyRequest, claimsApi, translateApi } from '../api';

interface AskWhyPanelProps {
  eventId: string;
  selectedActivityId?: string;
  onClose?: () => void;
}

export const AskWhyPanel: React.FC<AskWhyPanelProps> = ({
  eventId,
  selectedActivityId,
  onClose,
}) => {
  const [data, setData] = useState<AskWhyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [customQuestion, setCustomQuestion] = useState('');
  const { i18n } = useTranslation();
  // Feature 34: depth 1 = immediate context; selecting an upstream node re-roots the
  // traversal at that node and asks one level deeper.
  const [rootActivity, setRootActivity] = useState<string | undefined>(selectedActivityId);
  const [depth, setDepth] = useState(1);
  useEffect(() => {
    setRootActivity(selectedActivityId);
    setDepth(1);
  }, [selectedActivityId, eventId]);

  const fetchWhy = async (questionOverride?: string) => {
    try {
      setLoading(true);
      setError(null);
      const req: AskWhyRequest = {
        event_id: eventId,
        activity_id: rootActivity,
        depth,
        question: questionOverride || (customQuestion.trim() ? customQuestion.trim() : undefined),
      };
      const res = await claimsApi.askWhy(req);
      // Display-only runtime translation; falls back to the canonical English on failure.
      const lang = (i18n.language || 'en').slice(0, 2);
      if (lang !== 'en') {
        const steps = res.reasoning_steps || [];
        const translated = await translateApi.translate([res.explanation, ...steps], lang);
        setData({ ...res, explanation: translated[0], reasoning_steps: translated.slice(1) });
      } else {
        setData(res);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to generate explanation reasoning.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWhy();
  }, [eventId, rootActivity, depth, i18n.language]);

  const handleQuestionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customQuestion.trim()) return;
    fetchWhy(customQuestion.trim());
  };

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-xs space-y-4 text-foreground">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-teal-50 dark:bg-[#0A2340] text-[#14B8A6] dark:text-[#22D3EE] border border-teal-200 dark:border-[#1E3A5F]">
            <HelpCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              Explain Reasoning &amp; Graph Traversal
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950/80 text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-900/60">
                Ask Why
              </span>
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Inspect backend graph reasoning, entity lineage, and traversal depth for this match.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => fetchWhy()}
            disabled={loading}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-secondary transition-colors"
            title="Refresh Explanation"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-secondary transition-colors"
              title="Close Panel"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Custom Inquiry Input */}
      <form onSubmit={handleQuestionSubmit} className="flex gap-2">
        <input
          type="text"
          placeholder="Ask a specific question (e.g. Why was candidate #2 ranked lower?)..."
          value={customQuestion}
          onChange={(e) => setCustomQuestion(e.target.value)}
          className="flex-1 text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-[#1E3A5F] bg-white dark:bg-[#0A2340] text-slate-900 dark:text-[#F5F7FA] placeholder:text-slate-400 dark:placeholder:text-[#94A8B8] focus:outline-hidden focus:ring-2 focus:ring-[#FF7A18]"
        />
        <button
          type="submit"
          disabled={loading || !customQuestion.trim()}
          className="px-3.5 py-2 bg-gradient-to-r from-[#FF7A18] to-[#FF941F] hover:from-[#E06810] hover:to-[#FF7A18] disabled:opacity-50 text-white text-xs font-semibold rounded-lg inline-flex items-center gap-1.5 transition-all shadow-xs"
        >
          <Send className="w-3 h-3" />
          Ask
        </button>
      </form>

      {/* Body States */}
      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center text-muted-foreground">
          <RefreshCw className="w-6 h-6 animate-spin mb-2 text-[#14B8A6] dark:text-[#22D3EE]" />
          <p className="text-xs">Traversing knowledge graph &amp; synthesizing explanation...</p>
        </div>
      ) : error ? (
        <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Reasoning Explanation Unavailable</p>
            <p className="mt-0.5 text-amber-700 dark:text-amber-400">{error}</p>
            <button
              type="button"
              onClick={() => fetchWhy()}
              className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-[#FF7A18] underline hover:no-underline"
            >
              <RefreshCw className="w-3 h-3" /> Retry Reasoning Request
            </button>
          </div>
        </div>
      ) : !data ? (
        <div className="py-8 text-center text-muted-foreground text-xs">
          No reasoning data returned from backend service.
        </div>
      ) : (
        <div className="space-y-4">
          {/* Main Explanation Block */}
          <div className="p-3.5 rounded-xl bg-teal-50/60 dark:bg-[#0A2340]/90 border border-teal-200/80 dark:border-[#1E3A5F] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#061526] dark:text-[#F5F7FA] flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-[#FF7A18]" />
                Synthesized Decision Rationale
              </span>
              <button
                type="button"
                onClick={() => setDepth((d) => Math.min(d + 1, 6))}
                disabled={depth >= 6}
                className="text-[10px] font-semibold px-2 py-0.5 rounded-full border border-border bg-card hover:bg-muted disabled:opacity-40"
              >
                Go deeper
              </button>
              {data.traversal_depth != null && (
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950/80 text-cyan-800 dark:text-cyan-300 flex items-center gap-1 border border-cyan-200 dark:border-cyan-900/60">
                  <GitBranch className="w-3 h-3" />
                  Depth: {data.traversal_depth} {data.traversal_depth === 1 ? 'Hop' : 'Hops'}
                </span>
              )}
            </div>
            <p className="text-xs text-foreground/90 leading-relaxed font-medium">
              {data.explanation}
            </p>
          </div>

          {/* Reasoning Steps Sequence */}
          {data.reasoning_steps && data.reasoning_steps.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <ArrowRight className="w-3.5 h-3.5 text-[#14B8A6] dark:text-[#22D3EE]" />
                Traversal &amp; Validation Chain
              </h4>
              <div className="space-y-1.5">
                {data.reasoning_steps.map((step, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-card-subtle border border-border text-xs flex items-start gap-2.5"
                  >
                    <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-950/80 text-cyan-800 dark:text-cyan-300 shrink-0 border border-cyan-200 dark:border-cyan-900/60">
                      Step {idx + 1}
                    </span>
                    <span className="text-foreground/90">{step}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Entities & Evidence References Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {/* Entities Involved */}
            {data.entities_involved && data.entities_involved.length > 0 && (
              <div className="p-3 rounded-xl border border-border bg-card-subtle space-y-2">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Network className="w-3.5 h-3.5 text-[#14B8A6] dark:text-[#22D3EE]" />
                  Graph Entities Resolved
                </span>
                <div className="space-y-1">
                  {data.entities_involved.map((ent, idx) => {
                    // Upstream predecessors can be drilled into: re-root here and go one level deeper.
                    const drillable = ent.type === 'PREDECESSOR' && ent.name !== rootActivity;
                    return (
                      <div key={idx} className="flex items-center justify-between text-xs py-1 border-b border-border/60 last:border-0">
                        {drillable ? (
                          <button
                            type="button"
                            title="Investigate this activity (re-root, one level deeper)"
                            onClick={() => {
                              setRootActivity(ent.name);
                              setDepth((d) => Math.min(d + 1, 6));
                            }}
                            className="font-mono font-medium text-primary underline-offset-2 hover:underline cursor-pointer"
                          >
                            {ent.name}
                          </button>
                        ) : (
                          <span className="font-mono font-medium text-foreground">{ent.name}</span>
                        )}
                        <span className="text-[10px] font-medium text-muted-foreground">{ent.role}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Evidence References */}
            {data.evidence_references && data.evidence_references.length > 0 && (
              <div className="p-3 rounded-xl border border-border bg-card-subtle space-y-2">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <FileCheck2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  Corroborating Evidence
                </span>
                <div className="space-y-1">
                  {data.evidence_references.map((ref, idx) => (
                    <div key={idx} className="text-xs text-muted-foreground py-1 border-b border-border/60 last:border-0 flex items-center gap-1.5 truncate">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                      <span className="truncate text-foreground/90">{ref}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
