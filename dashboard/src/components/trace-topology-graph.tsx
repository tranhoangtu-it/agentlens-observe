// Trace topology graph — React Flow graph of spans with dagre hierarchical layout
// Running spans (no end_ms) get a CSS pulse animation; edges from running spans are dashed

import { useMemo, useCallback, memo } from 'react'
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from '@dagrejs/dagre'
import type { Span } from '../lib/api-client'
import { SPAN_TYPE_COLORS as TYPE_COLORS, DEFAULT_SPAN_COLOR } from '../lib/span-type-colors'

interface Props {
  spans: Span[]
  selectedSpanId: string | null
  onSelectSpan: (span: Span | null) => void
  replayRunningIds?: Set<string>   // optional — when provided, drives running state instead of end_ms == null
}

// Legend entries for span types
const TYPE_LABELS: { type: string; label: string; color: string }[] = [
  { type: 'agent_run', label: 'Agent Run',  color: TYPE_COLORS.agent_run },
  { type: 'tool_call', label: 'Tool Call',  color: TYPE_COLORS.tool_call },
  { type: 'llm_call',  label: 'LLM Call',   color: TYPE_COLORS.llm_call },
  { type: 'handoff',   label: 'Handoff',    color: TYPE_COLORS.handoff },
]

const NODE_W = 180
const NODE_H = 52

// CSS keyframes injected once for the pulse ring animation
const PULSE_STYLE = `
@keyframes agentlens-pulse-ring {
  0%   { box-shadow: 0 0 0 0px rgba(var(--pulse-color), 0.55); }
  70%  { box-shadow: 0 0 0 7px rgba(var(--pulse-color), 0); }
  100% { box-shadow: 0 0 0 0px rgba(var(--pulse-color), 0); }
}
.agentlens-node-running {
  animation: agentlens-pulse-ring 1.6s ease-out infinite;
}
`

// Inject style tag into document head (idempotent)
function ensurePulseStyle() {
  if (typeof document === 'undefined') return
  if (document.getElementById('agentlens-pulse-style')) return
  const el = document.createElement('style')
  el.id = 'agentlens-pulse-style'
  el.textContent = PULSE_STYLE
  document.head.appendChild(el)
}

function hexToRgb(hex: string): string {
  const h = hex.replace('#', '')
  const n = parseInt(h, 16)
  return `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`
}

function getNodeStyle(type: string, selected: boolean, running: boolean): React.CSSProperties {
  const color = TYPE_COLORS[type] ?? DEFAULT_SPAN_COLOR
  const rgbColor = hexToRgb(color)
  return {
    background: selected ? color : `${color}22`,
    border: `2px solid ${selected ? color : color + '99'}`,
    borderRadius: 8,
    color: '#f9fafb',
    fontSize: 12,
    padding: '6px 10px',
    width: NODE_W,
    boxShadow: selected ? `0 0 0 3px ${color}44` : undefined,
    ...(running ? { '--pulse-color': rgbColor } as React.CSSProperties : {}),
  }
}

// runningIds: set of span IDs considered in-progress; drives node pulse and edge dashing
function buildDagreLayout(spans: Span[], runningIds: Set<string>): { nodes: Node[]; edges: Edge[] } {
  ensurePulseStyle()

  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 60 })

  for (const s of spans) {
    g.setNode(s.id, { width: NODE_W, height: NODE_H })
  }
  for (const s of spans) {
    if (s.parent_id) g.setEdge(s.parent_id, s.id)
  }

  dagre.layout(g)

  const nodes: Node[] = spans.map((s) => {
    const pos = g.node(s.id)
    const running = runningIds.has(s.id)
    const dur = s.end_ms ? s.end_ms - s.start_ms : null
    const label = dur != null ? `${s.name}\n${dur}ms` : `${s.name}\n⏳ running`
    return {
      id: s.id,
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
      data: { label, span: s },
      style: getNodeStyle(s.type, false, running),
      className: running ? 'agentlens-node-running' : undefined,
    }
  })

  // Running span edges are dashed to signal in-progress connections
  const edges: Edge[] = spans
    .filter((s) => s.parent_id)
    .map((s) => {
      const isDashed = runningIds.has(s.id) || (s.parent_id ? runningIds.has(s.parent_id) : false)
      return {
        id: `e-${s.parent_id}-${s.id}`,
        source: s.parent_id!,
        target: s.id,
        style: {
          stroke: isDashed ? '#6b7280' : '#374151',
          strokeDasharray: isDashed ? '5 4' : undefined,
          strokeWidth: isDashed ? 1.5 : 1,
        },
        animated: isDashed,
      }
    })

  return { nodes, edges }
}

export const TraceTopologyGraph = memo(function TraceTopologyGraph({ spans, selectedSpanId, onSelectSpan, replayRunningIds }: Props) {
  // Replay mode: use replayRunningIds; live mode: derive from end_ms == null
  const effectiveRunningIds = useMemo(
    () => replayRunningIds ?? new Set(spans.filter((s) => s.end_ms == null).map((s) => s.id)),
    [spans, replayRunningIds],
  )

  const { nodes, edges } = useMemo(() => buildDagreLayout(spans, effectiveRunningIds), [spans, effectiveRunningIds])

  // Apply selected highlight on top of running state
  const styledNodes = useMemo(
    () =>
      nodes.map((n) => {
        const span = (n.data as { span: Span }).span
        // replay mode: running = replayRunningIds membership; live mode: running = end_ms == null
        const running = effectiveRunningIds.has(span.id)
        return {
          ...n,
          style: getNodeStyle(span.type, n.id === selectedSpanId, running),
          className: running ? 'agentlens-node-running' : undefined,
        }
      }),
    [nodes, selectedSpanId, effectiveRunningIds],
  )

  const onNodeClick: NodeMouseHandler = useCallback(
    (_evt, node) => {
      const span = (node.data as { span: Span }).span
      onSelectSpan(selectedSpanId === span.id ? null : span)
    },
    [onSelectSpan, selectedSpanId],
  )

  if (spans.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        No spans found for this trace.
      </div>
    )
  }

  // Collect which span types are actually present for the legend
  const presentTypes = new Set(spans.map((s) => s.type))
  const legendItems = TYPE_LABELS.filter((t) => presentTypes.has(t.type))

  return (
    <div className="relative" style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={styledNodes}
        edges={edges}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        colorMode="dark"
      >
        {/* Subtle dot-grid background */}
        <Background
          variant={BackgroundVariant.Dots}
          color="#1e293b"
          gap={20}
          size={1.5}
        />
        <Controls />
        <MiniMap
          nodeColor={(n) => {
            const span = (n.data as { span: Span }).span
            return TYPE_COLORS[span.type] ?? '#6b7280'
          }}
          maskColor="#0a0f1ecc"
          style={{ background: '#0f172a', border: '1px solid #1e293b' }}
        />
      </ReactFlow>

      {/* Type legend — bottom-left overlay */}
      {legendItems.length > 0 && (
        <div className="absolute bottom-3 left-3 z-10 flex items-center gap-3 px-3 py-1.5
                        bg-background/80 backdrop-blur-sm border border-border rounded-md text-xs
                        text-muted-foreground pointer-events-none">
          {legendItems.map((t) => (
            <span key={t.type} className="flex items-center gap-1.5">
              <span
                className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                style={{ background: t.color }}
              />
              {t.label}
            </span>
          ))}
        </div>
      )}
    </div>
  )
})
