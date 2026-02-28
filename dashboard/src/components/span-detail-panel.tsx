// Span detail side panel — shows name, type, duration, input/output, cost for selected span

import type { Span } from '../lib/api-client'

interface Props {
  span: Span
  onClose: () => void
}

function formatJson(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2)
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-3">
      <dt className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</dt>
      <dd className="text-sm text-gray-200">{value}</dd>
    </div>
  )
}

function CodeBlock({ label, value }: { label: string; value: unknown }) {
  const text = formatJson(value)
  return (
    <div className="mb-3">
      <dt className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</dt>
      <dd className="bg-gray-900 border border-gray-700 rounded p-2 text-xs font-mono text-gray-300 whitespace-pre-wrap max-h-40 overflow-y-auto">
        {text}
      </dd>
    </div>
  )
}

export function SpanDetailPanel({ span, onClose }: Props) {
  const duration = span.end_ms - span.start_ms

  return (
    <aside className="w-80 shrink-0 bg-gray-900 border-l border-gray-800 p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white truncate pr-2">{span.name}</h3>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-white transition-colors text-lg leading-none"
          aria-label="Close panel"
        >
          &times;
        </button>
      </div>

      <dl>
        <Row label="Type" value={span.type} />
        <Row label="Duration" value={`${duration}ms`} />
        {span.cost_model && <Row label="Model" value={span.cost_model} />}
        <Row
          label="Tokens"
          value={`${span.cost_input_tokens} in / ${span.cost_output_tokens} out`}
        />
        <Row
          label="Cost"
          value={span.cost_usd < 0.0001 ? '<$0.0001' : `$${span.cost_usd.toFixed(4)}`}
        />
        <CodeBlock label="Input" value={span.input} />
        <CodeBlock label="Output" value={span.output} />
      </dl>
    </aside>
  )
}
