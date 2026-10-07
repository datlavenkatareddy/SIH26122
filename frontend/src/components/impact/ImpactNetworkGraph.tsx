import React, { useMemo, useState, useRef, useEffect } from 'react';
import {
  ImpactPreviewResult,
  ImpactEvaluationItem,
} from '@/api';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Sparkles,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface ImpactNetworkGraphProps {
  data: ImpactPreviewResult;
  selectedActivityId: string | null;
  onSelectActivity: (id: string | null) => void;
}

interface GraphNode {
  id: string;
  name: string;
  depth: number;
  isOrigin: boolean;
  isControllingPath: boolean;
  isCompleted: boolean;
  uncertainty: boolean;
  executionState: string;
  grossDelay: number;
  netDelay: number;
  absorbedDelay: number;
  floatVal: number | null;
  floatStatus: string;
  relationship: string;
  controllingPred: string | null;
  targetPath: string[];
  rawItem?: ImpactEvaluationItem;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface GraphEdge {
  id: string;
  sourceId: string;
  targetId: string;
  relationship: string;
  lag: number;
  isControlling: boolean;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  midX: number;
  midY: number;
  pathD: string;
}

const NODE_WIDTH = 230;
const NODE_HEIGHT = 86;
const COL_SPACING = 380;
const ROW_SPACING = 120;
const PADDING_X = 60;
const PADDING_Y = 60;

export function ImpactNetworkGraph({
  data,
  selectedActivityId,
  onSelectActivity,
}: ImpactNetworkGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Zoom & Pan state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Controlling path identification from real A1 data
  const controllingPathSet = useMemo(() => {
    const set = new Set<string>();
    set.add(data.activity_id);
    for (const imp of data.impacts) {
      if (imp.net_delay_days && imp.net_delay_days > 0) {
        if (imp.target_path && Array.isArray(imp.target_path)) {
          imp.target_path.forEach((nodeId) => set.add(nodeId));
        } else {
          set.add(imp.successor_activity_id);
        }
      }
    }
    return set;
  }, [data]);

  // Compute Layout: Nodes and Edges
  const { nodes, edges, graphWidth, graphHeight, depthColumns, maxDepth } = useMemo(() => {
    const nodeMap = new Map<string, GraphNode>();
    const cols = new Map<number, GraphNode[]>();

    // 1. Origin Node (Depth 0)
    const originNode: GraphNode = {
      id: data.activity_id,
      name: data.activity_name || data.activity_id,
      depth: 0,
      isOrigin: true,
      isControllingPath: true,
      isCompleted: false,
      uncertainty: false,
      executionState: 'IN_PROGRESS',
      grossDelay: data.delay_days,
      netDelay: data.delay_days,
      absorbedDelay: 0,
      floatVal: 0,
      floatStatus: 'KNOWN',
      relationship: 'ORIGIN',
      controllingPred: null,
      targetPath: [data.activity_id],
      x: 0,
      y: 0,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    };

    nodeMap.set(data.activity_id, originNode);
    cols.set(0, [originNode]);

    // 2. Successor Nodes (Depth 1, 2, ...)
    let computedMaxDepth = 0;
    for (const imp of data.impacts) {
      const depth = Math.max(1, imp.propagation_depth || 1);
      computedMaxDepth = Math.max(computedMaxDepth, depth);
      const isCompleted = imp.execution_state === 'COMPLETED';
      const isControlling = controllingPathSet.has(imp.successor_activity_id);

      const nodeItem: GraphNode = {
        id: imp.successor_activity_id,
        name: imp.activity_name || imp.successor_activity_id,
        depth,
        isOrigin: false,
        isControllingPath: isControlling,
        isCompleted,
        uncertainty: imp.uncertainty,
        executionState: imp.execution_state || 'NOT_STARTED',
        grossDelay: imp.gross_delay_days,
        netDelay: imp.net_delay_days ?? 0,
        absorbedDelay: imp.absorbed_delay_days ?? 0,
        floatVal: imp.total_float,
        floatStatus: imp.float_status,
        relationship: imp.dependency_type || 'FS',
        controllingPred: imp.controlling_predecessor,
        targetPath: imp.target_path || [data.activity_id, imp.successor_activity_id],
        rawItem: imp,
        x: 0,
        y: 0,
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
      };

      nodeMap.set(imp.successor_activity_id, nodeItem);
      if (!cols.has(depth)) {
        cols.set(depth, []);
      }
      cols.get(depth)!.push(nodeItem);
    }

    // 3. Compute Dimensions
    let maxNodesInCol = 1;
    cols.forEach((colList) => {
      maxNodesInCol = Math.max(maxNodesInCol, colList.length);
    });

    const calculatedWidth = Math.max(920, PADDING_X * 2 + computedMaxDepth * COL_SPACING + NODE_WIDTH + 60);
    const calculatedHeight = Math.max(540, PADDING_Y * 2 + maxNodesInCol * ROW_SPACING);

    // 4. Assign Deterministic (X, Y) Coordinates per column
    cols.forEach((colList, depth) => {
      const colHeight = colList.length * ROW_SPACING - (ROW_SPACING - NODE_HEIGHT);
      const startY = Math.max(PADDING_Y, (calculatedHeight - colHeight) / 2);
      colList.forEach((node, idx) => {
        node.x = PADDING_X + depth * COL_SPACING;
        node.y = startY + idx * ROW_SPACING;
      });
    });

    // 5. Extract Causal Dependency Edges from A1 evaluation
    const edgeList: GraphEdge[] = [];
    const edgeKeySet = new Set<string>();

    for (const imp of data.impacts) {
      const targetId = imp.successor_activity_id;
      const targetNode = nodeMap.get(targetId);
      if (!targetNode) continue;

      if (imp.constraints_evaluated && imp.constraints_evaluated.length > 0) {
        for (const c of imp.constraints_evaluated) {
          const sourceId = c.predecessor_activity_id;
          if (!nodeMap.has(sourceId)) continue;

          const key = `${sourceId}->${targetId}`;
          if (!edgeKeySet.has(key)) {
            edgeKeySet.add(key);
            edgeList.push({
              id: key,
              sourceId,
              targetId,
              relationship: c.relationship_type || 'FS',
              lag: c.lag_days || 0,
              isControlling: Boolean(c.is_controlling && targetNode.netDelay > 0),
              x1: 0,
              y1: 0,
              x2: 0,
              y2: 0,
              midX: 0,
              midY: 0,
              pathD: '',
            });
          }
        }
      } else {
        // Fallback: use target_path or controlling_predecessor
        let sourceId = imp.controlling_predecessor;
        if (!sourceId || !nodeMap.has(sourceId)) {
          if (imp.target_path && imp.target_path.length >= 2) {
            const predCandidate = imp.target_path[imp.target_path.length - 2];
            if (nodeMap.has(predCandidate)) {
              sourceId = predCandidate;
            }
          }
        }
        if (!sourceId || !nodeMap.has(sourceId)) {
          sourceId = data.activity_id;
        }

        const key = `${sourceId}->${targetId}`;
        if (!edgeKeySet.has(key)) {
          edgeKeySet.add(key);
          edgeList.push({
            id: key,
            sourceId,
            targetId,
            relationship: imp.dependency_type || 'FS',
            lag: 0,
            isControlling: Boolean(targetNode.isControllingPath && targetNode.netDelay > 0),
            x1: 0,
            y1: 0,
            x2: 0,
            y2: 0,
            midX: 0,
            midY: 0,
            pathD: '',
          });
        }
      }
    }

    // 6. Compute Curved Paths & Midpoints for Edges
    const computedEdges: GraphEdge[] = edgeList.map((edge) => {
      const src = nodeMap.get(edge.sourceId)!;
      const tgt = nodeMap.get(edge.targetId)!;

      const x1 = src.x + NODE_WIDTH;
      const y1 = src.y + NODE_HEIGHT / 2;
      const x2 = tgt.x;
      const y2 = tgt.y + NODE_HEIGHT / 2;

      const dx = Math.max(40, x2 - x1);
      const cp1x = x1 + dx * 0.45;
      const cp1y = y1;
      const cp2x = x2 - dx * 0.45;
      const cp2y = y2;

      const pathD = `M ${x1} ${y1} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${x2} ${y2}`;

      // Parametric cubic Bezier midpoint at t = 0.5
      const midX = 0.125 * x1 + 0.375 * cp1x + 0.375 * cp2x + 0.125 * x2;
      const midY = 0.125 * y1 + 0.375 * cp1y + 0.375 * cp2y + 0.125 * y2;

      return {
        ...edge,
        x1,
        y1,
        x2,
        y2,
        midX,
        midY,
        pathD,
      };
    });

    return {
      nodes: Array.from(nodeMap.values()),
      edges: computedEdges,
      graphWidth: calculatedWidth,
      graphHeight: calculatedHeight,
      depthColumns: cols,
      maxDepth: computedMaxDepth,
    };
  }, [data, controllingPathSet]);

  const selectedNode = selectedActivityId
    ? nodes.find((n) => n.id === selectedActivityId)
    : null;

  // Pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  // Zoom controls
  const handleZoomIn = () => setZoom((z) => Math.min(2.0, Number((z + 0.15).toFixed(2))));
  const handleZoomOut = () => setZoom((z) => Math.max(0.4, Number((z - 0.15).toFixed(2))));
  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleFit = () => {
    if (!containerRef.current) return;
    const cw = containerRef.current.clientWidth;
    const ch = containerRef.current.clientHeight;
    const scaleX = (cw - 60) / graphWidth;
    const scaleY = (ch - 60) / graphHeight;
    const fitScale = Math.max(0.4, Math.min(1.2, Math.min(scaleX, scaleY)));
    setZoom(Number(fitScale.toFixed(2)));
    setPan({
      x: Math.max(20, (cw - graphWidth * fitScale) / 2),
      y: Math.max(20, (ch - graphHeight * fitScale) / 2),
    });
  };

  // Center or fit on initial mount or activity change
  useEffect(() => {
    handleFit();
  }, [data.activity_id, data.impacts.length]);

  return (
    <div className="space-y-4">
      {/* Legend Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 dark:bg-[#001438] rounded-xl border border-slate-200 dark:border-blue-900/40 text-[11px]">
        <div className="flex flex-wrap items-center gap-4 text-slate-600 dark:text-slate-300">
          <div className="flex items-center gap-1.5 font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-violet-600 shadow-xs" />
            <span>Target Origin</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
            <span>Direct Successors (Hop 1)</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
            <span>Downstream (Hop 2+)</span>
          </div>
          <div className="flex items-center gap-1.5 font-semibold text-rose-600 dark:text-rose-400">
            <span className="w-4 h-0.5 bg-rose-500 inline-block" />
            <span className="w-2 h-2 rounded-full bg-rose-500 -ml-2" />
            <span>Controlling Critical Slip Path</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Completed (Non-Propagating)</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium text-amber-600 dark:text-amber-400">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Uncertain Float</span>
          </div>
        </div>
        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
          Drag to pan · Click any node for factual inspector
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* SVG Network Graph Canvas */}
        <div
          className={cn(
            'transition-all duration-200',
            selectedNode ? 'lg:col-span-8' : 'lg:col-span-12'
          )}
        >
          <div
            ref={containerRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className={cn(
              'relative h-[600px] w-full rounded-2xl border border-slate-200 dark:border-blue-900/50 bg-slate-50/60 dark:bg-[#001230] overflow-hidden shadow-sm select-none',
              isDragging ? 'cursor-grabbing' : 'cursor-grab'
            )}
          >
            {/* SVG Background Pattern */}
            <svg
              ref={svgRef}
              className="w-full h-full block"
              style={{ touchAction: 'none' }}
            >
              <defs>
                {/* Dot Grid Pattern */}
                <pattern
                  id="network-grid-dots"
                  width="24"
                  height="24"
                  patternUnits="userSpaceOnUse"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="1"
                    className="fill-slate-300/60 dark:fill-blue-900/40"
                  />
                </pattern>

                {/* Normal Arrow Marker */}
                <marker
                  id="arrow-normal"
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path
                    d="M 0 1.5 L 8 5 L 0 8.5 z"
                    className="fill-slate-400 dark:fill-slate-500"
                  />
                </marker>

                {/* Controlling Arrow Marker */}
                <marker
                  id="arrow-controlling"
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#f43f5e" />
                </marker>
              </defs>

              {/* Background Grid */}
              <rect width="100%" height="100%" fill="url(#network-grid-dots)" />

              {/* Pan & Zoom Group */}
              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* 1. Depth Stage Column Header Indicators */}
                {Array.from(depthColumns.keys()).map((depth) => {
                  const colX = PADDING_X + depth * COL_SPACING;
                  const label =
                    depth === 0
                      ? 'Target Origin'
                      : depth === 1
                      ? 'Direct Successors'
                      : `Downstream Hop ${depth}`;

                  return (
                    <g key={`col-hdr-${depth}`} transform={`translate(${colX}, 28)`}>
                      <rect
                        x={0}
                        y={0}
                        width={NODE_WIDTH}
                        height={24}
                        rx={6}
                        className="fill-slate-200/60 dark:fill-blue-950/40 stroke-slate-300/70 dark:stroke-blue-800/40 stroke-[1]"
                      />
                      <text
                        x={NODE_WIDTH / 2}
                        y={16}
                        textAnchor="middle"
                        className="text-[10px] font-mono font-bold uppercase tracking-wider fill-slate-500 dark:fill-slate-400"
                      >
                        {label}
                      </text>
                    </g>
                  );
                })}

                {/* 2. Causal Dependency Edges Layer */}
                <g className="edges-layer">
                  {edges.map((edge) => {
                    const isControlling = edge.isControlling;
                    return (
                      <g key={edge.id}>
                        {/* Glow halo for controlling path */}
                        {isControlling && (
                          <path
                            d={edge.pathD}
                            fill="none"
                            stroke="#f43f5e"
                            strokeWidth={6}
                            strokeOpacity={0.25}
                            strokeLinecap="round"
                          />
                        )}
                        {/* Main dependency path */}
                        <path
                          d={edge.pathD}
                          fill="none"
                          stroke={isControlling ? '#f43f5e' : '#94a3b8'}
                          strokeWidth={isControlling ? 2.5 : 1.5}
                          markerEnd={
                            isControlling
                              ? 'url(#arrow-controlling)'
                              : 'url(#arrow-normal)'
                          }
                          className={cn(
                            'transition-all duration-150',
                            isControlling
                              ? 'dark:stroke-rose-500'
                              : 'dark:stroke-slate-600'
                          )}
                        />
                      </g>
                    );
                  })}
                </g>

                {/* 3. Edge Relationship & Lag Labels Layer */}
                <g className="edge-labels-layer">
                  {edges.map((edge) => {
                    const isControlling = edge.isControlling;
                    const lagStr =
                      edge.lag !== 0
                        ? edge.lag > 0
                          ? `+${edge.lag}d`
                          : `${edge.lag}d`
                        : '+0d';
                    const labelText = `${edge.relationship} ${lagStr}${
                      isControlling ? ' ★' : ''
                    }`;
                    const badgeWidth = labelText.length * 6.5 + 14;

                    return (
                      <g
                        key={`label-${edge.id}`}
                        transform={`translate(${edge.midX}, ${edge.midY})`}
                        className="pointer-events-none select-none"
                      >
                        <rect
                          x={-badgeWidth / 2}
                          y={-10}
                          width={badgeWidth}
                          height={20}
                          rx={4}
                          className={cn(
                            'transition-colors',
                            isControlling
                              ? 'fill-rose-50 dark:fill-rose-950/95 stroke-rose-400 dark:stroke-rose-600 stroke-[1.5] shadow-xs'
                              : 'fill-white dark:fill-[#001438] stroke-slate-300 dark:stroke-blue-900/80 stroke-[1]'
                          )}
                        />
                        <text
                          x={0}
                          y={3.5}
                          textAnchor="middle"
                          className={cn(
                            'text-[9px] font-mono font-bold tracking-tight',
                            isControlling
                              ? 'fill-rose-700 dark:fill-rose-300'
                              : 'fill-slate-600 dark:fill-slate-300'
                          )}
                        >
                          {labelText}
                        </text>
                      </g>
                    );
                  })}
                </g>

                {/* 4. Graph Nodes Layer (via HTML foreignObject) */}
                <g className="nodes-layer">
                  {nodes.map((node) => {
                    const isSelected = selectedActivityId === node.id;
                    return (
                      <foreignObject
                        key={node.id}
                        x={node.x}
                        y={node.y}
                        width={node.width}
                        height={node.height}
                        className="overflow-visible"
                      >
                        <div
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectActivity(isSelected ? null : node.id);
                          }}
                          className={cn(
                            'w-full h-full p-2.5 rounded-xl border text-xs cursor-pointer transition-all duration-150 flex flex-col justify-between select-none shadow-xs',
                            node.isOrigin
                              ? 'bg-violet-50/90 dark:bg-violet-950/40 border-violet-400 dark:border-violet-600 text-slate-900 dark:text-slate-100 shadow-sm'
                              : node.isControllingPath && node.netDelay > 0
                              ? 'bg-rose-50/90 dark:bg-rose-950/35 border-rose-400 dark:border-rose-600'
                              : node.depth === 1
                              ? 'bg-white dark:bg-[#001E60] border-blue-200 dark:border-blue-900/60 hover:border-blue-400 dark:hover:border-blue-700'
                              : 'bg-white dark:bg-[#001438] border-slate-200 dark:border-blue-900/40 hover:border-slate-300 dark:hover:border-blue-800',
                            isSelected &&
                              'ring-2 ring-violet-500 border-violet-500 dark:border-violet-400 shadow-md',
                            node.isCompleted &&
                              'opacity-80 bg-slate-50 dark:bg-slate-900/40'
                          )}
                        >
                          {/* Node Top Row: Activity ID & Net Delay Pill */}
                          <div className="flex items-center justify-between gap-1">
                            <span className="font-mono font-bold text-[11px] text-slate-900 dark:text-slate-100 truncate">
                              {node.id}
                            </span>
                            <span
                              className={cn(
                                'font-mono font-bold text-[9px] px-1.5 py-0.5 rounded-full shrink-0',
                                node.isOrigin
                                  ? 'bg-violet-100 dark:bg-violet-900/50 text-violet-700 dark:text-violet-300'
                                  : node.isCompleted
                                  ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                                  : node.netDelay > 0
                                  ? 'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400'
                                  : node.grossDelay > 0
                                  ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400'
                                  : 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                              )}
                            >
                              {node.isOrigin
                                ? `+${node.grossDelay}d ORIGIN`
                                : node.isCompleted
                                ? 'DONE (0d)'
                                : node.netDelay > 0
                                ? `+${node.netDelay}d NET`
                                : node.grossDelay > 0
                                ? `+${node.grossDelay}d ABS`
                                : '0d IMPACT'}
                            </span>
                          </div>

                          {/* Node Middle Row: Activity Name */}
                          <p
                            className="text-[11px] text-slate-600 dark:text-slate-300 truncate font-medium"
                            title={node.name}
                          >
                            {node.name}
                          </p>

                          {/* Node Bottom Row: Status / Depth tag */}
                          <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-100 dark:border-blue-900/30">
                            <span className="font-mono font-medium truncate max-w-[110px]">
                              {node.isOrigin ? 'ROOT CAUSE' : node.executionState}
                            </span>
                            {node.isCompleted ? (
                              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold text-[9px]">
                                <CheckCircle2 className="w-3 h-3" /> Done
                              </span>
                            ) : node.uncertainty ? (
                              <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-semibold text-[9px]">
                                <AlertTriangle className="w-3 h-3" /> Uncertain
                              </span>
                            ) : node.isControllingPath && !node.isOrigin ? (
                              <span className="text-[9px] font-bold text-rose-600 dark:text-rose-400">
                                ★ CONTROLLING
                              </span>
                            ) : (
                              <span className="text-[9px] text-slate-400">
                                {node.floatVal !== null
                                  ? `Float: ${node.floatVal}d`
                                  : 'Float: UNK'}
                              </span>
                            )}
                          </div>
                        </div>
                      </foreignObject>
                    );
                  })}
                </g>
              </g>
            </svg>

            {/* Floating Top-Right Zoom Controls Toolbar */}
            <div className="absolute top-3 right-3 flex items-center gap-1 bg-white/90 dark:bg-[#001438]/90 backdrop-blur-md border border-slate-200 dark:border-blue-900/60 p-1 rounded-xl shadow-md z-10 text-xs">
              <button
                type="button"
                onClick={handleZoomOut}
                title="Zoom Out"
                className="p-1.5 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="font-mono text-[11px] font-bold text-slate-700 dark:text-slate-300 px-1.5 min-w-[36px] text-center">
                {Math.round(zoom * 100)}%
              </span>
              <button
                type="button"
                onClick={handleZoomIn}
                title="Zoom In"
                className="p-1.5 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <div className="w-[1px] h-4 bg-slate-200 dark:bg-slate-700 mx-0.5" />
              <button
                type="button"
                onClick={handleFit}
                title="Fit to Viewport"
                className="p-1.5 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleReset}
                title="Reset View"
                className="p-1.5 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Floating Top-Left Breadcrumb / Status */}
            <div className="absolute top-3 left-3 flex items-center gap-2 bg-white/90 dark:bg-[#001438]/90 backdrop-blur-md border border-slate-200 dark:border-blue-900/60 px-3 py-1.5 rounded-xl shadow-xs z-10 text-[11px] font-mono text-slate-600 dark:text-slate-300">
              <span className="font-bold text-slate-900 dark:text-slate-100">
                {nodes.length} Nodes
              </span>
              <span>·</span>
              <span>{edges.length} Causal Edges</span>
              <span>·</span>
              <span className="text-violet-600 dark:text-violet-400 font-bold">
                Max Hop {maxDepth}
              </span>
            </div>
          </div>
        </div>

        {/* Factual Node Inspector Panel (Docked on right when a node is clicked) */}
        {selectedNode && (
          <div className="lg:col-span-4 animate-in fade-in slide-in-from-right-2 duration-200">
            <Card className="sticky top-4 bg-white dark:bg-[#001E60] border-slate-200 dark:border-blue-900/60 shadow-md">
              <CardHeader className="pb-3 border-b border-slate-200 dark:border-blue-900/40 flex flex-row items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100">
                      {selectedNode.id}
                    </CardTitle>
                    {selectedNode.isOrigin && (
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-900/50 text-violet-700 dark:text-violet-300">
                        ORIGIN
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {selectedNode.name}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onSelectActivity(null)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 cursor-pointer"
                >
                  ✕
                </button>
              </CardHeader>
              <CardContent className="pt-4 space-y-4 text-xs">
                {/* Status and State */}
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-[#001438] border border-slate-200 dark:border-blue-900/40">
                    <span className="text-[10px] text-slate-400 uppercase font-bold block">
                      Execution State
                    </span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200 font-mono">
                      {selectedNode.executionState}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-[#001438] border border-slate-200 dark:border-blue-900/40">
                    <span className="text-[10px] text-slate-400 uppercase font-bold block">
                      Propagation Depth
                    </span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200 font-mono">
                      {selectedNode.depth === 0
                        ? 'Origin (Root)'
                        : `Hop ${selectedNode.depth}`}
                    </span>
                  </div>
                </div>

                {/* Delay Breakdown Cards */}
                <div className="space-y-1.5 p-3 rounded-xl bg-slate-50 dark:bg-[#001438] border border-slate-200 dark:border-blue-900/40 text-[11px]">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                    A1 Delay Absorption Accounting
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-200 dark:border-blue-900/30">
                    <span className="text-slate-600 dark:text-slate-400">
                      Gross Delay:
                    </span>
                    <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                      +{selectedNode.grossDelay} days
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-200 dark:border-blue-900/30">
                    <span className="text-slate-600 dark:text-slate-400">
                      Total Float:
                    </span>
                    <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                      {selectedNode.floatStatus === 'KNOWN' &&
                      selectedNode.floatVal !== null
                        ? `${selectedNode.floatVal} days`
                        : 'UNKNOWN (Uncertain)'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-200 dark:border-blue-900/30">
                    <span className="text-slate-600 dark:text-slate-400">
                      Absorbed Delay:
                    </span>
                    <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                      {selectedNode.absorbedDelay} days
                    </span>
                  </div>
                  <div className="flex justify-between items-center pt-1.5 font-bold text-xs">
                    <span className="text-slate-900 dark:text-slate-100">
                      Net Impact:
                    </span>
                    <span
                      className={cn(
                        'font-mono',
                        selectedNode.netDelay > 0
                          ? 'text-rose-600 dark:text-rose-400'
                          : 'text-emerald-600 dark:text-emerald-400'
                      )}
                    >
                      +{selectedNode.netDelay} days
                    </span>
                  </div>
                </div>

                {/* Predecessor & Controlling Constraint */}
                {selectedNode.controllingPred && (
                  <div className="p-3 rounded-xl bg-violet-50/70 dark:bg-violet-950/20 border border-violet-200 dark:border-violet-900/40 text-[11px] space-y-1">
                    <span className="text-[10px] text-violet-600 dark:text-violet-400 font-bold uppercase block">
                      Controlling Predecessor
                    </span>
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                        {selectedNode.controllingPred}
                      </span>
                      <span className="font-mono text-[10px] bg-violet-100 dark:bg-violet-900/50 text-violet-700 dark:text-violet-300 px-2 py-0.5 rounded">
                        Rel: {selectedNode.relationship}
                      </span>
                    </div>
                  </div>
                )}

                {/* Causal Propagation Path */}
                {selectedNode.targetPath && selectedNode.targetPath.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[10px] text-slate-400 uppercase font-bold block">
                      Causal Propagation Path
                    </span>
                    <div className="flex items-center flex-wrap gap-1 p-2.5 rounded-lg bg-slate-50 dark:bg-[#001438] border border-slate-200 dark:border-blue-900/40 font-mono text-[11px]">
                      {selectedNode.targetPath.map((step, idx) => (
                        <React.Fragment key={idx}>
                          {idx > 0 && (
                            <ChevronRight className="w-3 h-3 text-slate-400 shrink-0" />
                          )}
                          <span
                            className={cn(
                              'px-1.5 py-0.5 rounded',
                              step === selectedNode.id
                                ? 'bg-violet-600 text-white font-bold'
                                : 'text-slate-700 dark:text-slate-300 font-medium'
                            )}
                          >
                            {step}
                          </span>
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                )}

                {/* Evaluated Constraints Count */}
                {selectedNode.rawItem?.constraints_evaluated &&
                  selectedNode.rawItem.constraints_evaluated.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[10px] text-slate-400 uppercase font-bold block">
                        Evaluated Incoming Constraints (
                        {selectedNode.rawItem.constraints_evaluated.length})
                      </span>
                      <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                        {selectedNode.rawItem.constraints_evaluated.map(
                          (c, i) => (
                            <div
                              key={i}
                              className={cn(
                                'p-2 rounded-lg border text-[10px] font-mono flex items-center justify-between',
                                c.is_controlling
                                  ? 'bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-900/40 text-rose-800 dark:text-rose-300'
                                  : 'bg-slate-50 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                              )}
                            >
                              <div>
                                <span className="font-bold">
                                  {c.predecessor_activity_id}
                                </span>{' '}
                                <span>({c.relationship_type})</span>
                                {c.lag_days !== 0 && (
                                  <span className="text-[9px] text-slate-400">
                                    {' '}
                                    lag: {c.lag_days}d
                                  </span>
                                )}
                              </div>
                              <span className="font-bold">
                                {c.is_controlling
                                  ? '★ Controlling'
                                  : 'Subordinate'}
                              </span>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}

                {/* Uncertainty Alert */}
                {selectedNode.uncertainty && (
                  <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 text-amber-800 dark:text-amber-300 text-[11px] flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500 mt-0.5" />
                    <span>
                      Total Float is null/unknown. Delay propagation is flagged
                      uncertain.
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
