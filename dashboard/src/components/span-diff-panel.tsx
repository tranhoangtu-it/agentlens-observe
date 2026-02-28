// span-diff-panel.tsx — Side-by-side span data diff for a matched span pair
// Shows cost/duration/token deltas and line-diffed input/output

import { useMemo } from 'react'
import { X } from 'lucide-react'
import { ScrollArea } from './ui/scroll-area'
import { Separator } from './ui/separator'
import type { Span, SpanMatchEntry } from '../lib/api-client'
import {
  diffText,
  formatCostDelta,
  formatDurationDelta,
  formatTokenDelta,
  formatPctChange,
  type DiffLine,
} from '../lib/diff-utils'

interface Props {
  matchEntry: SpanMatchEntry
  leftSpan: Span
  rightSpan: Span
  onClose: () => void
}

function DeltaRow({
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
  return (
    <div className="flex items-center gap-2 py-1.5 text-xs">
      <span className="text-muted-foreground w-20 shrink-0">{label}</span>
      <span className="text-foreground/70">{left}</span>
      <span className="text-muted-foreground">→</span>
      <span className="text-foreground/70">{right}</span>
      <span
        className={
          isPositive
            ? 'text-red-400 ml-auto font-mono'
            : isNegative
              ? 'text-green-400 ml-auto font-mono'
              : 'text-muted-foreground ml-auto font-mono'
        }
      >
        {delta}
        {pct}
      </span>
    </div>
  )
}

// Renders a unified diff block with color-coded lines
function DiffBlock({ lines, label }: { lines: DiffLine[]; label: string }) {
  if (lines.length === 0) return null
  const allUnchanged = lines.every((l) => l.type === 'unchanged')
  return (
    <div className="mt-3">
      <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1.5">{label}</p>
      <div className="rounded border border-border bg-card overflow-hidden">
        <pre className="p-3 text-xs font-mono whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">
          {lines.map((line, i) => {
            if (allUnchanged) {
              return (
                <span key={i} className="text-foreground/70">
                  {line.text}
                  {'\n'}
                </span>
              )
            }
            const cls =
              line.type === 'added'
                ? 'bg-green-950/60 text-green-300'
                : line.type === 'removed'
                  ? 'bg-red-950/60 text-red-300 line-through opacity-70'
                  : 'text-foreground/70'
            const prefix =
              line.type === 'added' ? '+ ' : line.type === 'removed' ? '- ' : '  '
            return (
              <span key={i} className={`block ${cls}`}>
                {prefix}
                {line.text}
              </span>
            )
          })}
        </pre>
      </div>
    </div>
  )
}

function formatVal(v: number | null | undefined, fmt: (n: number) => string): string {
  if (v == null) return '—'
  return fmt(v)
}

export function SpanDiffPanel({ matchEntry, leftSpan, rightSpan, onClose }: Props) {
  const leftDur = leftSpan.end_ms != null ? leftSpan.end_ms - leftSpan.start_ms : null
  const rightDur = rightSpan.end_ms != null ? rightSpan.end_ms - rightSpan.start_ms : null

  const inputDiff = useMemo(() => {
    const l = leftSpan.input != null ? String(leftSpan.input) : ''
    const r = rightSpan.input != null ? String(rightSpan.input) : ''
    return diffText(l, r)
  }, [leftSpan.input, rightSpan.input])

  const outputDiff = useMemo(() => {
    const l = leftSpan.output != null ? String(leftSpan.output) : ''
    const r = rightSpan.output != null ? String(rightSpan.output) : ''
    return diffText(l, r)
  }, [leftSpan.output, rightSpan.output])

  const statusColor =
    matchEntry.status === 'identical'
      ? 'text-green-400'
      : 'text-yellow-400'

  return (
    <aside className="w-96 shrink-0 bg-card border-l border-border flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-foreground truncate">{leftSpan.name}</h3>
          <span className={`text-xs ${statusColor}`}>
            {matchEntry.status === 'identical' ? 'Identical' : 'Changed'}
          </span>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors ml-2 shrink-0"
          aria-label="Close diff panel"
        >
          <X size={14} />
        </button>
      </div>

      {/* Scrollable body */}
      <ScrollArea className="flex-1">
        <div className="px-4 py-3 space-y-1">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">Deltas</p>

          <DeltaRow
            label="Duration"
            left={formatVal(leftDur, (v) => (v < 1000 ? `${v}ms` : `${(v / 1000).toFixed(2)}s`))}
            right={formatVal(rightDur, (v) => (v < 1000 ? `${v}ms` : `${(v / 1000).toFixed(2)}s`))}
            delta={formatDurationDelta(matchEntry.duration_delta_ms)}
            pct={formatPctChange(leftDur, rightDur)}
          />

          <DeltaRow
            label="Cost"
            left={formatVal(leftSpan.cost_usd, (v) => `$${v.toFixed(4)}`)}
            right={formatVal(rightSpan.cost_usd, (v) => `$${v.toFixed(4)}`)}
            delta={formatCostDelta(matchEntry.cost_delta_usd)}
            pct={formatPctChange(leftSpan.cost_usd, rightSpan.cost_usd)}
          />

          <DeltaRow
            label="In tokens"
            left={formatVal(leftSpan.cost_input_tokens, String)}
            right={formatVal(rightSpan.cost_input_tokens, String)}
            delta={formatTokenDelta(matchEntry.input_tokens_delta)}
            pct={formatPctChange(leftSpan.cost_input_tokens, rightSpan.cost_input_tokens)}
          />

          <DeltaRow
            label="Out tokens"
            left={formatVal(leftSpan.cost_output_tokens, String)}
            right={formatVal(rightSpan.cost_output_tokens, String)}
            delta={formatTokenDelta(matchEntry.output_tokens_delta)}
            pct={formatPctChange(leftSpan.cost_output_tokens, rightSpan.cost_output_tokens)}
          />

          <Separator className="my-3" />

          <DiffBlock lines={inputDiff} label="Input diff" />
          <DiffBlock lines={outputDiff} label="Output diff" />
        </div>
      </ScrollArea>
    </aside>
  )
}
