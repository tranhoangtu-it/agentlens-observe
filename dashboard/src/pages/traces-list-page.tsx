// Traces list page — fetches all traces, shows table, refreshes on SSE events

import { useState, useEffect, useCallback } from 'react'
import { fetchTraces, type Trace } from '../lib/api-client'
import { useSSETraces } from '../lib/use-sse-traces'
import { TraceListTable } from '../components/trace-list-table'

interface Props {
  onSelect: (id: string) => void
}

export function TracesListPage({ onSelect }: Props) {
  const [traces, setTraces] = useState<Trace[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { latestEvent, isConnected } = useSSETraces()

  const load = useCallback(async () => {
    try {
      const res = await fetchTraces()
      setTraces(res.traces)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load traces')
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load
  useEffect(() => { void load() }, [load])

  // Refresh on new SSE event
  useEffect(() => {
    if (latestEvent?.type === 'trace_created') void load()
  }, [latestEvent, load])

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">Traces</h2>
          <p className="text-gray-500 text-sm mt-0.5">
            {traces.length} trace{traces.length !== 1 ? 's' : ''} recorded
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-gray-600'
            }`}
          />
          {isConnected ? 'Live' : 'Disconnected'}
        </div>
      </div>

      {loading && (
        <p className="text-gray-500 text-sm">Loading traces…</p>
      )}
      {error && (
        <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/30 rounded p-3">
          {error}
        </p>
      )}
      {!loading && !error && (
        <TraceListTable traces={traces} onSelect={onSelect} />
      )}
    </div>
  )
}
