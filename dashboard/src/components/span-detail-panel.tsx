// Span detail side panel — shows name, type, duration, input/output, cost for selected span
// Uses Card and ScrollArea primitives for polished layout

import { memo } from 'react'
import type { Span } from '../lib/api-client'
import { Card, CardContent } from './ui/card'
import { ScrollArea } from './ui/scroll-area'
import { Separator } from './ui/separator'
import { X } from 'lucide-react'

interface Props {
  span: Span
  onClose: () => void
}

function formatJson(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2)
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-3 py-2">
      <span className="text-xs text-muted-foreground uppercase tracking-wide w-20 shrink-0 pt-0.5">
        {label}
      </span>
      <span className="text-sm text-foreground/90 break-all">{value}</span>
    </div>
  )
}

function CodeBlock({ label, value }: { label: string; value: unknown }) {
  const text = formatJson(value)
  return (
    <div className="mt-3">
      <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1.5">{label}</p>
      <Card>
        <CardContent className="p-0">
          <pre className="p-3 text-xs font-mono text-foreground/80 whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">
            {text}
          </pre>
        </CardContent>
      </Card>
    </div>
  )
}

export const SpanDetailPanel = memo(function SpanDetailPanel({ span, onClose }: Props) {
  const duration = span.end_ms - span.start_ms

  return (
    <aside className="w-80 shrink-0 bg-card border-l border-border flex flex-col animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <h3 className="text-sm font-semibold text-foreground truncate pr-2">{span.name}</h3>
        <button
          onClick={onClose}
          className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          aria-label="Close panel"
        >
          <X size={14} />
        </button>
      </div>

      {/* Scrollable body */}
      <ScrollArea className="flex-1">
        <div className="px-4 py-3">
          <dl>
            <MetaRow label="Type"     value={span.type} />
            <MetaRow label="Duration" value={`${duration}ms`} />
            {span.cost_model && <MetaRow label="Model" value={span.cost_model} />}
            <MetaRow
              label="Tokens"
              value={`${span.cost_input_tokens} in / ${span.cost_output_tokens} out`}
            />
            <MetaRow
              label="Cost"
              value={span.cost_usd < 0.0001 ? '<$0.0001' : `$${span.cost_usd.toFixed(4)}`}
            />
          </dl>

          <Separator className="my-3" />

          <CodeBlock label="Input"  value={span.input} />
          <CodeBlock label="Output" value={span.output} />
        </div>
      </ScrollArea>
    </aside>
  )
})
