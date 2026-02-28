// trace-compare-page.tsx — Main side-by-side trace comparison page
// Fetches comparison data, renders header stats, two topology graphs, and span diff panel

import { useState, useEffect } from 'react'
import { fetchTraceComparison, type SpanMatchEntry, type Span } from '../lib/api-client'
import type { TraceCompareResponse } from '../lib/api-client'
import { TraceCompareHeader } from '../components/trace-compare-header'
import { TraceCompareGraphs } from '../components/trace-compare-graphs'
import { SpanDiffPanel } from '../components/span-diff-panel'
import { Skeleton } from '../components/ui/skeleton'
import { ArrowLeft } from 'lucide-react'

interface Props {
  leftId: string
  rightId: string
  onBack: () => void
}

function buildSpanIndex(spans: Span[]): Record<string, Span> {
  const idx: Record<string, Span> = {}
  for (const s of spans) idx[s.id] = s
  return idx
}

export function TraceComparePage({ leftId, rightId, onBack }: Props) {
  const [data, setData] = useState<TraceCompareResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedMatch, setSelectedMatch] = useState<SpanMatchEntry | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    setSelectedMatch(null)
    fetchTraceComparison(leftId, rightId)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load comparison'))
      .finally(() => setLoading(false))
  }, [leftId, rightId])

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="flex gap-4">
          <Skeleton className="h-64 flex-1" />
          <Skeleton className="h-64 flex-1" />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
        >
          <ArrowLeft size={14} /> Back
        </button>
        <p className="text-red-400 text-sm bg-destructive/10 border border-destructive/30 rounded-md p-3">
          {error ?? 'No data returned'}
        </p>
      </div>
    )
  }

  const leftSpans = data.left.spans as Span[]
  const rightSpans = data.right.spans as Span[]
  const leftIndex = buildSpanIndex(leftSpans)
  const rightIndex = buildSpanIndex(rightSpans)

  // Resolve Span objects for the selected match entry
  const leftSpan = selectedMatch ? leftIndex[selectedMatch.left_span_id] : null
  const rightSpan = selectedMatch ? rightIndex[selectedMatch.right_span_id] : null

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Back navigation */}
      <div className="shrink-0 px-4 py-2 border-b border-border">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={12} /> Back to traces
        </button>
      </div>

      {/* Diff summary header */}
      <TraceCompareHeader
        leftTrace={data.left.trace}
        rightTrace={data.right.trace}
        diff={data.diff}
      />

      {/* Graphs + optional diff panel */}
      <div className="flex-1 flex overflow-hidden">
        <TraceCompareGraphs
          leftSpans={leftSpans}
          rightSpans={rightSpans}
          leftTraceId={leftId}
          rightTraceId={rightId}
          diff={data.diff}
          selectedMatch={selectedMatch}
          onSelectMatch={setSelectedMatch}
        />

        {selectedMatch && leftSpan && rightSpan && (
          <SpanDiffPanel
            matchEntry={selectedMatch}
            leftSpan={leftSpan}
            rightSpan={rightSpan}
            onClose={() => setSelectedMatch(null)}
          />
        )}
      </div>
    </div>
  )
}
