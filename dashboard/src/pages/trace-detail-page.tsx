// Trace detail page — topology graph + span detail panel + cost chart for a single trace
// Uses useLiveTraceDetail for real-time SSE updates while trace is running

import { useState } from 'react'
import { useLiveTraceDetail } from '../lib/use-live-trace-detail'
import type { Span } from '../lib/api-client'
import { TraceTopologyGraph } from '../components/trace-topology-graph'
import { SpanDetailPanel } from '../components/span-detail-panel'
import { CostSummaryChart } from '../components/cost-summary-chart'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'
import { ArrowLeft, Play } from 'lucide-react'

interface Props {
  traceId: string
  onBack: () => void
  onReplay?: (id: string) => void
}

export function TraceDetailPage({ traceId, onBack, onReplay }: Props) {
  const { trace, spans, loading, error, isLive } = useLiveTraceDetail(traceId)
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null)

  return (
    <div className="flex flex-col h-full">
      {/* Sub-header */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-border shrink-0">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors text-sm"
        >
          <ArrowLeft size={14} />
          Back
        </button>
        <div className="h-4 w-px bg-border" />

        {loading ? (
          <div className="flex items-center gap-3">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-48" />
          </div>
        ) : (
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <span className="text-sm font-semibold text-foreground truncate">
              {trace?.agent_name ?? traceId}
            </span>
            <span className="text-xs text-muted-foreground font-mono truncate hidden sm:block">
              {traceId}
            </span>

            {isLive && (
              <Badge variant="running" className="shrink-0">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse mr-1" />
                Live
              </Badge>
            )}

            {trace && (
              <span className="text-xs text-muted-foreground shrink-0">
                {spans.length} span{spans.length !== 1 ? 's' : ''}
              </span>
            )}

            {/* Replay button — only shown for completed traces */}
            {trace && onReplay && trace.status !== 'running' && (
              <button
                onClick={() => onReplay(traceId)}
                className="ml-auto flex items-center gap-1.5 text-xs px-2.5 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors shrink-0"
              >
                <Play size={11} />
                Replay
              </button>
            )}

            {/* Hint when trace is still running */}
            {trace && trace.status === 'running' && (
              <span className="ml-auto text-xs text-muted-foreground italic shrink-0">
                Replay available after trace completes
              </span>
            )}
          </div>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="p-6 text-red-400 text-sm bg-destructive/10 border border-destructive/30 rounded-md m-5">
          {error}
        </div>
      )}

      {/* Loading skeleton for graph area */}
      {loading && (
        <div className="flex-1 flex flex-col gap-4 p-5">
          <Skeleton className="flex-1 w-full rounded-lg" />
          <div className="flex gap-3">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
      )}

      {!loading && !error && (
        <>
          {/* Main content: graph + side panel */}
          <div className="flex flex-1 overflow-hidden">
            <div className="flex-1 overflow-hidden">
              <TraceTopologyGraph
                spans={spans}
                selectedSpanId={selectedSpan?.id ?? null}
                onSelectSpan={setSelectedSpan}
              />
            </div>
            {selectedSpan && (
              <SpanDetailPanel
                span={selectedSpan}
                onClose={() => setSelectedSpan(null)}
              />
            )}
          </div>

          {/* Cost chart footer */}
          <div className="shrink-0 border-t border-border px-5 pt-3 pb-2">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Cost by Model
            </h3>
            <CostSummaryChart spans={spans} />
          </div>
        </>
      )}
    </div>
  )
}
