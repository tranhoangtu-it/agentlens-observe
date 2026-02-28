// trace-compare-graphs.tsx — Two React Flow topology graphs side-by-side
// Nodes are color-coded by diff status: green=identical, yellow=changed, red=left-only, blue=right-only
// Clicking a matched pair opens the span diff panel via onSelectMatch

import { useMemo, useCallback } from 'react'
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from '@dagrejs/dagre'
import type { Span, TraceDiff, SpanMatchEntry } from '../lib/api-client'

// Diff status colors
const DIFF_COLORS = {
  identical: '#22c55e',  // green-500
  changed:   '#eab308',  // yellow-500
  left_only: '#ef4444',  // red-500
  right_only:'#3b82f6',  // blue-500
  unknown:   '#6b7280',  // gray-500
}

const NODE_W = 180
const NODE_H = 52

interface DiffStatusMap {
  [spanId: string]: 'identical' | 'changed' | 'left_only' | 'right_only'
}

// Map span id -> matched partner id (for click correlation)
interface MatchMap {
  [spanId: string]: SpanMatchEntry
}

function buildStatusMaps(diff: TraceDiff): { statusMap: DiffStatusMap; matchMap: MatchMap } {
  const statusMap: DiffStatusMap = {}
  const matchMap: MatchMap = {}

  for (const m of diff.matched) {
    statusMap[m.left_span_id] = m.status
    statusMap[m.right_span_id] = m.status
    matchMap[m.left_span_id] = m
    matchMap[m.right_span_id] = m
  }
  for (const id of diff.left_only) {
    statusMap[id] = 'left_only'
  }
  for (const id of diff.right_only) {
    statusMap[id] = 'right_only'
  }

  return { statusMap, matchMap }
}

function getNodeStyle(
  _spanType: string,
  diffStatus: string,
  selected: boolean,
): React.CSSProperties {
  const color = DIFF_COLORS[diffStatus as keyof typeof DIFF_COLORS] ?? DIFF_COLORS.unknown
  return {
    background: selected ? color : `${color}22`,
    border: `2px solid ${selected ? color : color + '88'}`,
    borderRadius: 8,
    color: '#f9fafb',
    fontSize: 11,
    padding: '6px 10px',
    width: NODE_W,
    boxShadow: selected ? `0 0 0 3px ${color}44` : undefined,
    cursor: diffStatus === 'identical' || diffStatus === 'changed' ? 'pointer' : 'default',
  }
}

function buildLayout(
  spans: Span[],
  statusMap: DiffStatusMap,
  selectedMatchId: string | null,
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 60 })

  for (const s of spans) g.setNode(s.id, { width: NODE_W, height: NODE_H })
  for (const s of spans) {
    if (s.parent_id) g.setEdge(s.parent_id, s.id)
  }
  dagre.layout(g)

  const nodes: Node[] = spans.map((s) => {
    const pos = g.node(s.id)
    const status = statusMap[s.id] ?? 'unknown'
    const dur = s.end_ms != null ? s.end_ms - s.start_ms : null
    const label = dur != null ? `${s.name}\n${dur}ms` : `${s.name}\n⏳`
    const isSelected = s.id === selectedMatchId
    return {
      id: s.id,
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
      data: { label, span: s, diffStatus: status },
      style: getNodeStyle(s.type, status, isSelected),
    }
  })

  const edges: Edge[] = spans
    .filter((s) => s.parent_id)
    .map((s) => ({
      id: `e-${s.parent_id}-${s.id}`,
      source: s.parent_id!,
      target: s.id,
      style: { stroke: '#374151', strokeWidth: 1 },
    }))

  return { nodes, edges }
}

// Single graph panel with label
function GraphPanel({
  label,
  spans,
  statusMap,
  matchMap,
  selectedMatchSpanId,
  onSelectMatch,
}: {
  label: string
  spans: Span[]
  statusMap: DiffStatusMap
  matchMap: MatchMap
  selectedMatchSpanId: string | null
  onSelectMatch: (entry: SpanMatchEntry | null) => void
}) {
  const { nodes, edges } = useMemo(
    () => buildLayout(spans, statusMap, selectedMatchSpanId),
    [spans, statusMap, selectedMatchSpanId],
  )

  const onNodeClick: NodeMouseHandler = useCallback(
    (_evt, node) => {
      const entry = matchMap[node.id]
      if (!entry) return
      const isSame =
        node.id === selectedMatchSpanId ||
        entry.left_span_id === selectedMatchSpanId ||
        entry.right_span_id === selectedMatchSpanId
      onSelectMatch(isSame ? null : entry)
    },
    [matchMap, selectedMatchSpanId, onSelectMatch],
  )

  if (spans.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm border-r border-border last:border-r-0">
        No spans
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-w-0 border-r border-border last:border-r-0">
      <div className="shrink-0 px-3 py-1.5 border-b border-border bg-muted/30">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
      </div>
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          colorMode="dark"
        >
          <Background variant={BackgroundVariant.Dots} color="#1e293b" gap={20} size={1.5} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  )
}

// Diff color legend
function DiffLegend() {
  const items = [
    { label: 'Identical', color: DIFF_COLORS.identical },
    { label: 'Changed',   color: DIFF_COLORS.changed },
    { label: 'Left only', color: DIFF_COLORS.left_only },
    { label: 'Right only',color: DIFF_COLORS.right_only },
  ]
  return (
    <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-3
                    px-3 py-1.5 bg-background/80 backdrop-blur-sm border border-border
                    rounded-md text-xs text-muted-foreground pointer-events-none">
      {items.map((it) => (
        <span key={it.label} className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full shrink-0" style={{ background: it.color }} />
          {it.label}
        </span>
      ))}
    </div>
  )
}

interface Props {
  leftSpans: Span[]
  rightSpans: Span[]
  leftTraceId: string
  rightTraceId: string
  diff: TraceDiff
  selectedMatch: SpanMatchEntry | null
  onSelectMatch: (entry: SpanMatchEntry | null) => void
}

export function TraceCompareGraphs({
  leftSpans,
  rightSpans,
  leftTraceId,
  rightTraceId,
  diff,
  selectedMatch,
  onSelectMatch,
}: Props) {
  const { statusMap, matchMap } = useMemo(() => buildStatusMaps(diff), [diff])

  // Determine which span IDs are "selected" in each graph
  const selectedLeftId = selectedMatch?.left_span_id ?? null
  const selectedRightId = selectedMatch?.right_span_id ?? null

  return (
    <div className="flex-1 flex relative overflow-hidden">
      <GraphPanel
        label={`Left — ${leftTraceId}`}
        spans={leftSpans}
        statusMap={statusMap}
        matchMap={matchMap}
        selectedMatchSpanId={selectedLeftId}
        onSelectMatch={onSelectMatch}
      />
      <GraphPanel
        label={`Right — ${rightTraceId}`}
        spans={rightSpans}
        statusMap={statusMap}
        matchMap={matchMap}
        selectedMatchSpanId={selectedRightId}
        onSelectMatch={onSelectMatch}
      />
      <DiffLegend />
    </div>
  )
}
