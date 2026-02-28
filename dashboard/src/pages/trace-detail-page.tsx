// Trace detail page — topology graph + span detail panel + cost chart for a single trace

import { useState, useEffect } from 'react'
import { fetchTrace, type Trace, type Span } from '../lib/api-client'
import { TraceTopologyGraph } from '../components/trace-topology-graph'
import { SpanDetailPanel } from '../components/span-detail-panel'
import { CostSummaryChart } from '../components/cost-summary-chart'

interface Props {
  traceId: string
  onBack: () => void
}

export function TraceDetailPage({ traceId, onBack }: Props) {
  const [trace, setTrace] = useState<Trace | null>(null)
  const [spans, setSpans] = useState<Span[]>([])
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setSelectedSpan(null)
    fetchTrace(traceId)
      .then((res) => {
        setTrace(res.trace)
        setSpans(res.spans)
        setError(null)
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Failed to load trace')
      })
      .finally(() => setLoading(false))
  }, [traceId])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-800 shrink-0">
        <button
          onClick={onBack}
          className="text-gray-400 hover:text-white transition-colors text-sm"
        >
          &larr; Back
        </button>
        <div className="h-4 w-px bg-gray-700" />
        <div>
          <span className="text-sm font-semibold text-white">
            {trace?.agent_name ?? traceId}
          </span>
          <span className="ml-3 text-xs text-gray-500 font-mono">{traceId}</span>
        </div>
      </div>

      {loading && (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          Loading trace…
        </div>
      )}
      {error && (
        <div className="p-6 text-red-400 text-sm bg-red-500/10 border border-red-500/30 rounded m-6">
          {error}
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
          <div className="shrink-0 border-t border-gray-800 px-6 pt-4 pb-2">
            <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
              Cost by Model
            </h3>
            <CostSummaryChart spans={spans} />
          </div>
        </>
      )}
    </div>
  )
}
