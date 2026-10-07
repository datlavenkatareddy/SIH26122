import React, { useRef, useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Calendar, GitBranch, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ImpactPreviewResult } from '@/api';
import { cn } from '@/lib/utils';

interface PrecedenceRippleGraphProps {
  result: ImpactPreviewResult;
  originActivityName?: string;
  className?: string;
}

interface EdgePath {
  idx: number;
  d: string;
  midX: number;
  midY: number;
  label: string;
}

export function PrecedenceRippleGraph({
  result,
  originActivityName,
  className,
}: PrecedenceRippleGraphProps) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const originRef = useRef<HTMLDivElement>(null);
  const successorRefs = useRef<(HTMLDivElement | null)[]>([]);

  const [edgePaths, setEdgePaths] = useState<EdgePath[]>([]);
  const [hoveredIndex, setHoveredIndex] = useState<number | 'origin' | null>(null);

  const calculateEdges = useCallback(() => {
    if (!containerRef.current || !originRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    const originRect = originRef.current.getBoundingClientRect();

    // Origin right-center anchor
    const x1 = originRect.right - containerRect.left;
    const y1 = originRect.top + originRect.height / 2 - containerRect.top;

    const paths: EdgePath[] = [];

    successorRefs.current.forEach((succEl, idx) => {
      if (!succEl) return;
      const succRect = succEl.getBoundingClientRect();
      // Successor left-center anchor
      const x2 = succRect.left - containerRect.left;
      const y2 = succRect.top + succRect.height / 2 - containerRect.top;

      const dx = Math.max(x2 - x1, 40);
      const cx1 = x1 + dx * 0.45;
      const cy1 = y1;
      const cx2 = x2 - dx * 0.45;
      const cy2 = y2;
      const d = `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;

      // Cubic bezier midpoint at t = 0.5
      const midX = 0.125 * x1 + 0.375 * cx1 + 0.375 * cx2 + 0.125 * x2;
      const midY = 0.125 * y1 + 0.375 * cy1 + 0.375 * cy2 + 0.125 * y2;

      const rel = result.successors[idx]?.relationship_type || 'FS';
      paths.push({ idx, d, midX, midY, label: rel });
    });

    setEdgePaths(paths);
  }, [result]);

  useEffect(() => {
    const timer = setTimeout(calculateEdges, 60);
    window.addEventListener('resize', calculateEdges);

    const ro = new ResizeObserver(() => {
      calculateEdges();
    });

    if (containerRef.current) {
      ro.observe(containerRef.current);
    }

    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', calculateEdges);
      ro.disconnect();
    };
  }, [calculateEdges]);

  const hasSuccessors = result.successors && result.successors.length > 0;

  return (
    <Card className={cn('border-slate-200/80 dark:border-[#214766] bg-white/95 dark:bg-[#071A2D]/95 shadow-xl rounded-2xl overflow-hidden', className)}>
      <CardHeader className="p-5 pb-4 border-b border-slate-300 dark:border-[#214766]/60 flex flex-row items-center justify-between gap-4">
        <div>
          <CardTitle className="text-sm font-extrabold flex items-center gap-2 text-[#071A2D] dark:text-[#F5F7FA]">
            <div className="p-1 rounded-md bg-teal-50 dark:bg-[#0A2340] border border-teal-200 dark:border-[#1E3A5F]">
              <GitBranch className="w-4 h-4 text-[#14B8A6] dark:text-[#22D3EE]" />
            </div>
            <span>{t('impact.rippleGraphTitle')}</span>
          </CardTitle>
          <p className="text-[11px] text-[#475569] dark:text-[#9FB2C3] font-medium mt-0.5">
            {t('impact.scopeDisclaimer')}
          </p>
        </div>

        <span className="text-[11px] bg-rose-500/10 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-300 dark:border-rose-500/30 px-3 py-1 rounded-full font-mono font-bold shrink-0 shadow-xs">
          +{result.delay_days}d SHIFT
        </span>
      </CardHeader>

      <CardContent className="p-4 sm:p-6">
        {/* Interactive Graph Canvas Area */}
        <div
          ref={containerRef}
          className="relative min-h-[280px] w-full rounded-xl border border-slate-200/80 dark:border-[#214766] bg-slate-50/60 dark:bg-[#0A2238] p-4 sm:p-6 overflow-x-auto"
        >
          {/* SVG Connection Layer */}
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none z-0 overflow-visible"
            style={{ minWidth: '100%', minHeight: '100%' }}
          >
            <defs>
              {/* Default Direction Arrow */}
              <marker
                id="arrow-cyan"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#0284C7" />
              </marker>

              {/* Active / Hover Direction Arrow */}
              <marker
                id="arrow-orange"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#FF7A18" />
              </marker>
            </defs>

            {/* Render Curved Edges */}
            {edgePaths.map((edge) => {
              const isHovered = hoveredIndex === edge.idx || hoveredIndex === 'origin';
              return (
                <g key={edge.idx}>
                  {/* Invisible thicker path for easier hover targeting */}
                  <path
                    d={edge.d}
                    fill="none"
                    stroke="transparent"
                    strokeWidth="16"
                    className="pointer-events-auto cursor-pointer"
                    onMouseEnter={() => setHoveredIndex(edge.idx)}
                    onMouseLeave={() => setHoveredIndex(null)}
                  />

                  {/* Visible Curved Edge */}
                  <path
                    d={edge.d}
                    fill="none"
                    stroke={isHovered ? '#FF7A18' : '#0284C7'}
                    strokeWidth={isHovered ? 3 : 2}
                    markerEnd={isHovered ? 'url(#arrow-orange)' : 'url(#arrow-cyan)'}
                    className="transition-all duration-200"
                  />
                </g>
              );
            })}
          </svg>

          {/* Floating Relationship Labels along curves */}
          {edgePaths.map((edge) => {
            const isHovered = hoveredIndex === edge.idx || hoveredIndex === 'origin';
            return (
              <div
                key={`label-${edge.idx}`}
                className={cn(
                  'absolute z-20 -translate-x-1/2 -translate-y-1/2 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border shadow-xs transition-all duration-200 cursor-pointer pointer-events-auto',
                  isHovered
                    ? 'bg-[#FF7A18] text-white border-orange-400 scale-110 shadow-orange-500/30'
                    : 'bg-white dark:bg-[#071A2D] text-[#0284C7] dark:text-[#38BDF8] border-sky-300 dark:border-[#214766]'
                )}
                style={{ left: `${edge.midX}px`, top: `${edge.midY}px` }}
                onMouseEnter={() => setHoveredIndex(edge.idx)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                {edge.label}
              </div>
            );
          })}

          {/* Graph Nodes Layout: Left (Origin) -> Right (Successors) */}
          <div className="relative z-10 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-10 sm:gap-14 min-w-[560px] sm:min-w-0">
            {/* 1. IMPACT ORIGIN NODE */}
            <div
              ref={originRef}
              onMouseEnter={() => setHoveredIndex('origin')}
              onMouseLeave={() => setHoveredIndex(null)}
              className={cn(
                'relative w-full sm:w-60 shrink-0 p-4 rounded-xl border-2 transition-all duration-200 shadow-md',
                hoveredIndex === 'origin'
                  ? 'border-[#FF7A18] ring-2 ring-[#FF7A18]/30 shadow-orange-500/20 bg-amber-50 dark:bg-amber-950/70'
                  : 'border-[#FF7A18]/80 bg-amber-50/70 dark:bg-[#15120E] border-amber-400/80 dark:border-amber-600/70'
              )}
            >
              {/* Right Output Connector Port */}
              <div className="hidden sm:block absolute -right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full bg-[#FF7A18] border-2 border-white dark:border-[#071A2D] shadow-sm z-30" />

              {/* Node Header */}
              <div className="flex items-center justify-between gap-1.5 mb-2">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-[#FF7A18] dark:text-[#FF941F] flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {t('impact.impactOrigin')}
                </span>
                <span className="text-[10px] bg-[#FF7A18] text-white font-mono font-bold px-1.5 py-0.5 rounded-full shadow-xs">
                  +{result.delay_days}d ORIGIN
                </span>
              </div>

              {/* Activity Identifier */}
              <div className="font-mono font-extrabold text-[#071A2D] dark:text-[#F5F7FA] text-base truncate">
                {result.activity_id}
              </div>

              {/* Activity Name */}
              <div className="text-xs text-[#334155] dark:text-[#C5D2DE] font-semibold mt-1 line-clamp-2">
                {originActivityName || result.activity_id}
              </div>

              {/* Delay Metric Tag */}
              <div className="mt-3 pt-2 border-t border-amber-200 dark:border-amber-900/60 flex items-center justify-between text-[11px] font-mono">
                <span className="text-[#64748B] dark:text-[#9FB2C3]">Hypothetical:</span>
                <span className="font-bold text-[#FF7A18] dark:text-[#FF941F]">+{result.delay_days} days</span>
              </div>
            </div>

            {/* 2. SUCCESSOR NODES COLUMN */}
            <div className="flex-1 space-y-4 w-full">
              {!hasSuccessors ? (
                <div className="p-6 rounded-xl border border-dashed border-slate-300 dark:border-[#214766] bg-white/60 dark:bg-[#071A2D]/60 text-center space-y-2">
                  <AlertCircle className="w-6 h-6 text-slate-400 dark:text-slate-500 mx-auto" />
                  <div className="text-xs font-bold text-[#071A2D] dark:text-[#F5F7FA]">
                    No immediate Finish-to-Start successors
                  </div>
                  <div className="text-[11px] text-[#475569] dark:text-[#9FB2C3]">
                    This activity has no downstream FS dependencies affected by the hypothetical delay.
                  </div>
                </div>
              ) : (
                result.successors.map((succ, idx) => {
                  const isHovered = hoveredIndex === idx || hoveredIndex === 'origin';
                  return (
                    <div
                      key={succ.successor_activity_id || idx}
                      ref={(el) => {
                        successorRefs.current[idx] = el;
                      }}
                      onMouseEnter={() => setHoveredIndex(idx)}
                      onMouseLeave={() => setHoveredIndex(null)}
                      className={cn(
                        'relative p-4 rounded-xl border-2 transition-all duration-200 shadow-md',
                        isHovered
                          ? 'border-[#0284C7] dark:border-[#38BDF8] ring-2 ring-sky-500/20 bg-sky-50/50 dark:bg-[#0D2942] scale-[1.01]'
                          : 'border-slate-300 dark:border-[#214766] bg-white dark:bg-[#0A2238]'
                      )}
                    >
                      {/* Left Input Connector Port */}
                      <div className="hidden sm:block absolute -left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full bg-[#0284C7] dark:bg-[#38BDF8] border-2 border-white dark:border-[#071A2D] shadow-sm z-30" />

                      {/* Header Row */}
                      <div className="flex items-center justify-between gap-2 flex-wrap mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-extrabold text-xs text-[#0284C7] dark:text-[#38BDF8] bg-sky-100/70 dark:bg-sky-950/80 px-2 py-0.5 rounded-md border border-sky-300 dark:border-sky-800/80">
                            {succ.successor_activity_id}
                          </span>
                          <span className="text-[10px] font-mono font-bold bg-slate-100 dark:bg-[#152E48] text-[#334155] dark:text-[#C5D2DE] px-2 py-0.5 rounded-full border border-slate-200 dark:border-[#214766]">
                            {succ.relationship_type || 'FS'}
                          </span>
                        </div>

                        <span className="text-[10px] bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-300 dark:border-rose-900/60 font-mono font-bold px-2 py-0.5 rounded-full shadow-xs">
                          +{result.delay_days}d SHIFT
                        </span>
                      </div>

                      {/* Activity Name */}
                      <div className="font-bold text-xs text-[#071A2D] dark:text-[#F5F7FA]">
                        {succ.activity_name}
                      </div>

                      {/* Date Ripple Comparison Grid */}
                      <div className="grid grid-cols-2 gap-3 text-[11px] font-mono pt-2.5 mt-2.5 border-t border-slate-200 dark:border-[#214766]">
                        <div className="space-y-0.5">
                          <span className="text-[#64748B] dark:text-[#9FB2C3] text-[10px] uppercase font-bold tracking-wide block">
                            {t('impact.originalStart')}
                          </span>
                          <span className="text-[#071A2D] dark:text-[#F5F7FA] font-bold">
                            {succ.original_start || '—'}
                          </span>
                        </div>

                        <div className="space-y-0.5">
                          <span className="text-[#64748B] dark:text-[#9FB2C3] text-[10px] uppercase font-bold tracking-wide block">
                            {t('impact.shiftedStart')}
                          </span>
                          <span className="font-extrabold text-rose-600 dark:text-rose-400">
                            {succ.shifted_start || '—'}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default PrecedenceRippleGraph;
