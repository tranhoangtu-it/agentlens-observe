// Traces list page — search, filters, sortable table, pagination, SSE refresh
// Supports compare mode: activate with "Compare" button, select 2 traces, click "Compare Selected"

import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchTraces, fetchAgents, type Trace } from '../lib/api-client'
import { useTraceFilters } from '../lib/use-trace-filters'
import { useSSETraces } from '../lib/use-sse-traces'
import { TraceListTable } from '../components/trace-list-table'
import { TraceSearchBar } from '../components/trace-search-bar'
import { TraceFilterControls } from '../components/trace-filter-controls'
import { PaginationControls } from '../components/pagination-controls'
import { Skeleton } from '../components/ui/skeleton'

interface Props {
  onSelect: (id: string) => void
  onCompare?: (leftId: string, rightId: string) => void
}

export function TracesListPage({ onSelect, onCompare }: Props) {
  const [traces, setTraces] = useState<Trace[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [agents, setAgents] = useState<string[]>([])
  const [compareMode, setCompareMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  const { filters, setFilter, resetFilters, apiParams } = useTraceFilters()
  const { latestEvent, isConnected } = useSSETraces()

  const prevParamsRef = useRef<string>('')

  const load = useCallback(async (params = apiParams) => {
    const key = JSON.stringify(params)
    prevParamsRef.current = key
    setLoading(true)
    try {
      const res = await fetchTraces(params)
      setTraces(res.traces)
      setTotal(res.total)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load traces')
    } finally {
      setLoading(false)
    }
  }, [apiParams]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchAgents()
      .then((r) => setAgents(r.agents))
      .catch(() => {/* non-critical */})
  }, [])

  useEffect(() => {
    void load(apiParams)
  }, [apiParams]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const t = latestEvent?.type
    if (t === 'trace_created' || t === 'trace_updated') {
      prevParamsRef.current = ''
      void load(apiParams)
    }
  }, [latestEvent]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleSort(col: string) {
    if (filters.sort === col) {
      setFilter('order', filters.order === 'desc' ? 'asc' : 'desc')
    } else {
      setFilter('sort', col)
      setFilter('order', 'desc')
    }
  }

  function toggleCompareMode() {
    setCompareMode((prev) => !prev)
    setSelectedIds([])
  }

  function handleToggleSelect(id: string) {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= 2) return prev
      return [...prev, id]
    })
  }

  function handleCompareSelected() {
    if (selectedIds.length === 2 && onCompare) {
      onCompare(selectedIds[0], selectedIds[1])
    }
  }

  return (
    <div className="p-6 space-y-4 overflow-y-auto h-full">
      {/* Header row */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Traces</h2>
          <p className="text-muted-foreground text-xs mt-0.5">
            {loading ? 'Loading…' : `${total.toLocaleString()} trace${total !== 1 ? 's' : ''}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Compare mode controls */}
          {onCompare && (
            compareMode ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  {selectedIds.length}/2 selected
                </span>
                {selectedIds.length === 2 && (
                  <button
                    onClick={handleCompareSelected}
                    className="text-xs px-2.5 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors font-medium"
                  >
                    Compare Selected
                  </button>
                )}
                <button
                  onClick={toggleCompareMode}
                  className="text-xs px-2.5 py-1 rounded border border-border text-muted-foreground hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={toggleCompareMode}
                className="text-xs px-2.5 py-1 rounded border border-border text-muted-foreground hover:text-foreground transition-colors"
              >
                Compare
              </button>
            )
          )}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-muted-foreground/40'
              }`}
            />
            <span className={isConnected ? 'text-green-400' : ''}>
              {isConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Search bar */}
      <TraceSearchBar
        value={filters.q}
        onChange={(v) => setFilter('q', v)}
      />

      {/* Filter controls */}
      <TraceFilterControls
        filters={filters}
        agents={agents}
        onFilter={setFilter}
        onReset={resetFilters}
      />

      {/* Error */}
      {error && (
        <p className="text-red-400 text-sm bg-destructive/10 border border-destructive/30 rounded-md p-3">
          {error}
        </p>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-2">
          {/* Header row skeleton */}
          <div className="flex gap-3 pb-2 border-b border-border">
            {[120, 80, 60, 80, 80, 100].map((w, i) => (
              <Skeleton key={i} className="h-3" style={{ width: w }} />
            ))}
          </div>
          {/* Data row skeletons */}
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex gap-3 items-center py-1.5">
              <Skeleton className="h-3.5 w-28" />
              <Skeleton className="h-5 w-16 rounded" />
              <Skeleton className="h-3.5 w-8" />
              <Skeleton className="h-3.5 w-16" />
              <Skeleton className="h-3.5 w-14" />
              <Skeleton className="h-3.5 w-24" />
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      {!loading && !error && (
        <TraceListTable
          traces={traces}
          onSelect={onSelect}
          sort={filters.sort}
          order={filters.order}
          onSort={handleSort}
          compareMode={compareMode}
          selectedIds={selectedIds}
          onToggleSelect={handleToggleSelect}
        />
      )}

      {/* Pagination */}
      {!loading && !error && total > 0 && (
        <PaginationControls
          total={total}
          page={filters.page}
          pageSize={filters.pageSize}
          onPageChange={(p) => setFilter('page', p)}
          onPageSizeChange={(s) => setFilter('pageSize', s)}
        />
      )}
    </div>
  )
}
