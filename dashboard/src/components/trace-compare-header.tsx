// trace-compare-header.tsx — Summary stats diff bar for trace comparison page
// Shows cost, duration, span count, token diffs between left and right traces

import type { Trace, TraceDiff } from '../lib/api-client'
import { formatCostDelta, formatDurationDelta, formatPctChange } from '../lib/diff-utils'

interface Props {
  leftTrace: Trace
  rightTrace: Trace
  diff: TraceDiff
}

function StatCard({
  label,
  left,
  right,
  delta,
  pct,
}: {
  label: string
  left: string
  right: string
  delta: string
  pct?: string
}) {
  const isPositive = delta.startsWith('+')
  const isNegative = delta.startsWith('-') && delta !== '—'
  const deltaColor = isPositive
    ? 'text-red-400'
    : isNegative
      ? 'text-green-400'
      : 'text-muted-foreground'

  return (
    <div className="flex flex-col gap-0.5 px-4 py-2.5 border-r border-border last:border-r-0 min-w-0">
      <span className="text-xs text-muted-foreground uppercase tracking-wide">{label}</span>
      <div className="flex items-baseline gap-1.5 text-sm">
        <span className="text-foreground/60 font-mono text-xs">{left}</span>
        <span className="text-muted-foreground text-xs">→</span>
        <span className="text-foreground font-mono text-xs">{right}</span>
      </div>
      <span className={`text-xs font-mono font-medium ${deltaColor}`}>
        {delta}
        {pct && <span className="text-muted-foreground font-normal">{pct}</span>}
      </span>
    </div>
  )
}

function DiffLegend({ diff }: { diff: TraceDiff }) {
  const identical = diff.matched.filter((m) => m.status === 'identical').length
  const changed = diff.matched.filter((m) => m.status === 'changed').length
  const leftOnly = diff.left_only.length
  const rightOnly = diff.right_only.length

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 text-xs">
      {identical > 0 && (
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-green-500" />
          <span className="text-muted-foreground">{identical} identical</span>
        </span>
      )}
      {changed > 0 && (
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-yellow-500" />
          <span className="text-muted-foreground">{changed} changed</span>
        </span>
      )}
      {leftOnly > 0 && (
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500" />
          <span className="text-muted-foreground">{leftOnly} left only</span>
        </span>
      )}
      {rightOnly > 0 && (
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-500" />
          <span className="text-muted-foreground">{rightOnly} right only</span>
        </span>
      )}
    </div>
  )
}

function fmt(v: number | null | undefined, fn: (n: number) => string): string {
  return v == null ? '—' : fn(v)
}

export function TraceCompareHeader({ leftTrace, rightTrace, diff }: Props) {
  const costDelta = (leftTrace.total_cost_usd != null && rightTrace.total_cost_usd != null)
    ? rightTrace.total_cost_usd - leftTrace.total_cost_usd
    : null

  const durDelta = (leftTrace.duration_ms != null && rightTrace.duration_ms != null)
    ? rightTrace.duration_ms - leftTrace.duration_ms
    : null

  const spanDelta = rightTrace.span_count - leftTrace.span_count
  const spanDeltaStr = spanDelta === 0 ? '0' : spanDelta > 0 ? `+${spanDelta}` : `${spanDelta}`

  const tokenDelta = (leftTrace.total_tokens != null && rightTrace.total_tokens != null)
    ? rightTrace.total_tokens - leftTrace.total_tokens
    : null
  const tokenDeltaStr = tokenDelta == null
    ? '—'
    : tokenDelta === 0 ? '0' : tokenDelta > 0 ? `+${tokenDelta}` : `${tokenDelta}`

  return (
    <div className="shrink-0 border-b border-border bg-card">
      {/* Trace IDs row */}
      <div className="flex items-center px-4 py-2 border-b border-border gap-4 text-xs">
        <div className="flex items-center gap-2 min-w-0">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 shrink-0" />
          <span className="text-muted-foreground shrink-0">Left:</span>
          <span className="font-mono text-foreground/80 truncate">{leftTrace.agent_name}</span>
          <span className="text-muted-foreground font-mono truncate max-w-xs">{leftTrace.id}</span>
        </div>
        <div className="flex items-center gap-2 min-w-0">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-500 shrink-0" />
          <span className="text-muted-foreground shrink-0">Right:</span>
          <span className="font-mono text-foreground/80 truncate">{rightTrace.agent_name}</span>
          <span className="text-muted-foreground font-mono truncate max-w-xs">{rightTrace.id}</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex items-stretch divide-x divide-border">
        <StatCard
          label="Cost"
          left={fmt(leftTrace.total_cost_usd, (v) => `$${v.toFixed(4)}`)}
          right={fmt(rightTrace.total_cost_usd, (v) => `$${v.toFixed(4)}`)}
          delta={formatCostDelta(costDelta)}
          pct={formatPctChange(leftTrace.total_cost_usd, rightTrace.total_cost_usd)}
        />
        <StatCard
          label="Duration"
          left={fmt(leftTrace.duration_ms, (v) => v < 1000 ? `${v}ms` : `${(v / 1000).toFixed(2)}s`)}
          right={fmt(rightTrace.duration_ms, (v) => v < 1000 ? `${v}ms` : `${(v / 1000).toFixed(2)}s`)}
          delta={formatDurationDelta(durDelta)}
          pct={formatPctChange(leftTrace.duration_ms, rightTrace.duration_ms)}
        />
        <StatCard
          label="Spans"
          left={String(leftTrace.span_count)}
          right={String(rightTrace.span_count)}
          delta={spanDeltaStr}
        />
        <StatCard
          label="Tokens"
          left={fmt(leftTrace.total_tokens, String)}
          right={fmt(rightTrace.total_tokens, String)}
          delta={tokenDeltaStr}
          pct={formatPctChange(leftTrace.total_tokens, rightTrace.total_tokens)}
        />
        <DiffLegend diff={diff} />
      </div>
    </div>
  )
}
