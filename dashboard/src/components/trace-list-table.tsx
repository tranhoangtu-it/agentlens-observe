// Trace list table — shows all traces with status badges, click to navigate to detail

import type { Trace } from '../lib/api-client'

interface Props {
  traces: Trace[]
  onSelect: (id: string) => void
}

const STATUS_CLASSES: Record<string, string> = {
  completed: 'bg-green-500/20 text-green-400 border border-green-500/40',
  running: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40',
  error: 'bg-red-500/20 text-red-400 border border-red-500/40',
}

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_CLASSES[status] ?? 'bg-gray-500/20 text-gray-400 border border-gray-500/40'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {status}
    </span>
  )
}

function formatCost(usd: number): string {
  return usd < 0.0001 ? '<$0.0001' : `$${usd.toFixed(4)}`
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

export function TraceListTable({ traces, onSelect }: Props) {
  if (traces.length === 0) {
    return (
      <div className="text-center py-16 text-gray-500">
        No traces yet. Run an agent to see data here.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-gray-400 text-left">
            <th className="pb-3 pr-4 font-medium">Agent</th>
            <th className="pb-3 pr-4 font-medium">Status</th>
            <th className="pb-3 pr-4 font-medium">Spans</th>
            <th className="pb-3 pr-4 font-medium">Cost</th>
            <th className="pb-3 pr-4 font-medium">Duration</th>
            <th className="pb-3 font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {traces.map((t) => (
            <tr
              key={t.id}
              onClick={() => onSelect(t.id)}
              className="border-b border-gray-800/60 hover:bg-gray-800/40 cursor-pointer transition-colors"
            >
              <td className="py-3 pr-4 font-mono text-blue-400">{t.agent_name}</td>
              <td className="py-3 pr-4">
                <StatusBadge status={t.status} />
              </td>
              <td className="py-3 pr-4 text-gray-300">{t.span_count}</td>
              <td className="py-3 pr-4 text-gray-300">{formatCost(t.total_cost_usd)}</td>
              <td className="py-3 pr-4 text-gray-300">{formatDuration(t.duration_ms)}</td>
              <td className="py-3 text-gray-400 text-xs">{formatDate(t.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
