// Trace replay page — time-travel debugging for a completed trace
// Route: #/traces/:id/replay
// Client-side only: fetches trace once, replays spans via cursor offset

import { useState, useEffect, useMemo } from 'react'
import { fetchTrace } from '../lib/api-client'
import type { Trace, Span } from '../lib/api-client'
import { useReplayControls } from '../lib/use-replay-controls'
import { TraceTopologyGraph } from '../components/trace-topology-graph'
import { SpanDetailPanel } from '../components/span-detail-panel'
import { CostSummaryChart } from '../components/cost-summary-chart'
import { ReplayTransportControls } from '../components/replay-transport-controls'
import { ReplayTimelineScrubber } from '../components/replay-timeline-scrubber'
import { Skeleton } from '../components/ui/skeleton'
import { ArrowLeft } from 'lucide-react'

interface Props {
  traceId: string
  onBack: () => void   // navigate to #/traces/:id
}

export function TraceReplayPage({ traceId, onBack }: Props) {
  const [trace, setTrace] = useState<Trace | null>(null)
  const [spans, setSpans] = useState<Span[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch once — no SSE
  useEffect(() => {
    fetchTrace(traceId)
      .then((res) => {
        // Sort by start_ms for deterministic replay
        const sorted = [...res.spans].sort((a, b) => a.start_ms - b.start_ms)
        setTrace(res.trace)
        setSpans(sorted)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load trace'))
      .finally(() => setLoading(false))
  }, [traceId])

  // Absolute ms of first span — replay offset base
  const traceStart = useMemo(
    () => (spans.length ? spans[0].start_ms : 0),
    [spans],
  )

  // Fallback: compute duration from max end_ms if duration_ms is 0
  const duration = useMemo(() => {
    if (trace && trace.duration_ms > 0) return trace.duration_ms
    if (!spans.length) return 0
    const maxEnd = Math.max(...spans.map((s) => s.end_ms))
    return maxEnd - traceStart
  }, [trace, spans, traceStart])

  const { cursor, isPlaying, speed, play, pause, seek, stepForward, stepBack, setSpeed } =
    useReplayControls(spans, duration)

  // Spans that have started at current cursor position
  const filteredSpans = useMemo(
    () => spans.filter((s) => s.start_ms - traceStart <= cursor),
    [spans, cursor, traceStart],
  )

  // Spans that started but haven't ended yet at cursor — shown as "running" in graph
  const replayRunningIds = useMemo(
    () => new Set(filteredSpans.filter((s) => s.end_ms - traceStart > cursor).map((s) => s.id)),
    [filteredSpans, cursor, traceStart],
  )

  // Auto-select most recently started span at cursor
  const activeSpan = filteredSpans.length ? filteredSpans[filteredSpans.length - 1] : null

  if (loading) {
    return (
      <div className="flex flex-col h-full gap-4 p-5">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="flex-1 w-full rounded-lg" />
        <Skeleton className="h-16 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 text-red-400 text-sm bg-destructive/10 border border-destructive/30 rounded-md m-5">
        {error}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Sub-header */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-border shrink-0">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-sm"
        >
          <ArrowLeft size={14} />
          Detail
        </button>
        <div className="h-4 w-px bg-border" />
        <span className="text-sm font-semibold text-foreground truncate">
          Replay — {trace?.agent_name ?? traceId}
        </span>
        <span className="text-xs text-muted-foreground font-mono hidden sm:block truncate max-w-xs">
          {traceId}
        </span>
        <span className="text-xs text-muted-foreground ml-auto shrink-0">
          {filteredSpans.length}/{spans.length} spans
        </span>
      </div>

      {/* Main: graph + side panel */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-hidden">
          <TraceTopologyGraph
            spans={filteredSpans}
            selectedSpanId={activeSpan?.id ?? null}
            onSelectSpan={() => {}}   // auto-selection only in replay mode
            replayRunningIds={replayRunningIds}
          />
        </div>
        {activeSpan && (
          <SpanDetailPanel
            span={activeSpan}
            onClose={() => {}}   // no manual close in replay mode
          />
        )}
      </div>

      {/* Bottom replay bar */}
      <div className="shrink-0 border-t border-border px-5 py-3 flex flex-col gap-2 bg-card">
        <div className="flex items-center gap-4">
          <ReplayTransportControls
            isPlaying={isPlaying}
            speed={speed}
            onPlay={play}
            onPause={pause}
            onStepBack={stepBack}
            onStepForward={stepForward}
            onSpeedChange={setSpeed}
          />
          <div className="flex-1">
            <ReplayTimelineScrubber
              spans={spans}
              cursor={cursor}
              duration={duration}
              traceStart={traceStart}
              onSeek={seek}
            />
          </div>
        </div>
        {/* Cumulative cost at cursor */}
        {filteredSpans.length > 0 && (
          <div className="pt-1">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">
              Cost at cursor
            </p>
            <CostSummaryChart spans={filteredSpans} />
          </div>
        )}
      </div>
    </div>
  )
}
