// Trace topology graph — React Flow graph of spans with dagre hierarchical layout

import { useMemo, useCallback } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from '@dagrejs/dagre'
import type { Span } from '../lib/api-client'

interface Props {
  spans: Span[]
  selectedSpanId: string | null
  onSelectSpan: (span: Span | null) => void
}

// Node color by span type
const TYPE_COLORS: Record<string, string> = {
  agent_run: '#3b82f6',   // blue-500
  tool_call: '#22c55e',   // green-500
  llm_call:  '#a855f7',   // purple-500
  handoff:   '#f97316',   // orange-500
}

const NODE_W = 180
const NODE_H = 52

function getNodeStyle(type: string, selected: boolean) {
  const color = TYPE_COLORS[type] ?? '#6b7280'
  return {
    background: selected ? color : `${color}22`,
    border: `2px solid ${color}`,
    borderRadius: 8,
    color: '#f9fafb',
    fontSize: 12,
    padding: '6px 10px',
    width: NODE_W,
  }
}

function buildDagreLayout(spans: Span[]): { nodes: Node[]; edges: Edge[] } {
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
    const dur = s.end_ms - s.start_ms
    const label = `${s.name}\n${dur}ms`
    return {
      id: s.id,
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
      data: { label, span: s },
      style: getNodeStyle(s.type, false),
    }
  })

  const edges: Edge[] = spans
    .filter((s) => s.parent_id)
    .map((s) => ({
      id: `e-${s.parent_id}-${s.id}`,
      source: s.parent_id!,
      target: s.id,
      style: { stroke: '#4b5563' },
    }))

  return { nodes, edges }
}

export function TraceTopologyGraph({ spans, selectedSpanId, onSelectSpan }: Props) {
  const { nodes, edges } = useMemo(() => buildDagreLayout(spans), [spans])

  // Apply selected highlight
  const styledNodes = useMemo(
    () =>
      nodes.map((n) => {
        const span = (n.data as { span: Span }).span
        return { ...n, style: getNodeStyle(span.type, n.id === selectedSpanId) }
      }),
    [nodes, selectedSpanId],
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
      <div className="flex items-center justify-center h-full text-gray-500">
        No spans found for this trace.
      </div>
    )
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
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
        <Background color="#374151" gap={24} />
        <Controls />
        <MiniMap
          nodeColor={(n) => {
            const span = (n.data as { span: Span }).span
            return TYPE_COLORS[span.type] ?? '#6b7280'
          }}
          maskColor="#111827cc"
        />
      </ReactFlow>
    </div>
  )
}
