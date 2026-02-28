// Replay timeline scrubber — Gantt bars + range slider for trace replay
// Gantt bars show all spans; slider controls cursor position (0..duration ms)

import { memo, useCallback } from 'react'
import type { Span } from '../lib/api-client'
import { SPAN_TYPE_COLORS, DEFAULT_SPAN_COLOR } from '../lib/span-type-colors'

interface Props {
  spans: Span[]          // all spans, sorted by start_ms
  cursor: number         // current ms offset from traceStart
  duration: number       // total trace duration_ms
  traceStart: number     // absolute ms of first span start
  onSeek: (ms: number) => void
}

function pct(value: number, total: number): string {
  if (total === 0) return '0%'
  return `${Math.min(100, (value / total) * 100).toFixed(2)}%`
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

export const ReplayTimelineScrubber = memo(function ReplayTimelineScrubber({
  spans, cursor, duration, traceStart, onSeek,
}: Props) {
  const handleSlider = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => onSeek(Number(e.target.value)),
    [onSeek],
  )

  const handleBarClick = useCallback(
    (span: Span) => onSeek(span.start_ms - traceStart),
    [onSeek, traceStart],
  )

  const cursorPct = pct(cursor, duration)

  return (
    <div className="flex flex-col gap-1.5 select-none">
      {/* Gantt area */}
      <div
        className="relative bg-muted/30 border border-border rounded overflow-y-auto"
        style={{ maxHeight: 160 }}
      >
        {/* Cursor line */}
        <div
          className="absolute top-0 bottom-0 w-px bg-primary/70 z-10 pointer-events-none"
          style={{ left: cursorPct }}
        />

        {/* Span bars */}
        <div className="flex flex-col gap-px py-1 px-0 min-h-[32px]">
          {spans.map((span) => {
            const startOffset = span.start_ms - traceStart
            const endMs = span.end_ms ?? (traceStart + duration)
            const spanDur = Math.max(1, endMs - span.start_ms)
            const endOffset = endMs - traceStart
            const color = SPAN_TYPE_COLORS[span.type] ?? DEFAULT_SPAN_COLOR
            const isActive = startOffset <= cursor && endOffset > cursor

            return (
              <div
                key={span.id}
                className="relative h-[18px] mx-1"
                title={`${span.name} (${formatMs(startOffset)}–${formatMs(endOffset)})`}
              >
                <div
                  className="absolute h-full rounded-sm cursor-pointer transition-opacity"
                  style={{
                    left: pct(startOffset, duration),
                    width: pct(spanDur, duration),
                    background: color,
                    opacity: isActive ? 1 : 0.35,
                    border: isActive ? `1px solid ${color}` : '1px solid transparent',
                  }}
                  onClick={() => handleBarClick(span)}
                />
              </div>
            )
          })}
        </div>
      </div>

      {/* Range slider */}
      <input
        type="range"
        min={0}
        max={duration}
        step={1}
        value={cursor}
        onChange={handleSlider}
        className="w-full accent-primary h-1.5 cursor-pointer"
      />

      {/* Time labels */}
      <div className="flex justify-between text-[10px] text-muted-foreground font-mono px-0.5">
        <span>0</span>
        <span className="text-primary font-semibold">{formatMs(cursor)}</span>
        <span>{formatMs(duration)}</span>
      </div>
    </div>
  )
})
