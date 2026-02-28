// Trace list table — sortable headers, status badges, click to navigate to detail
// Supports optional compare-mode with checkboxes (max 2 selections)
// Uses ui/table and ui/badge primitives

import type { Trace } from '../lib/api-client'
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from './ui/table'
import { Badge, type BadgeProps } from './ui/badge'

interface Props {
  traces: Trace[]
  onSelect: (id: string) => void
  sort?: string
  order?: string
  onSort?: (col: string) => void
  compareMode?: boolean
  selectedIds?: string[]
  onToggleSelect?: (id: string) => void
}

// Map status string to Badge variant
const STATUS_VARIANT: Record<string, BadgeProps['variant']> = {
  completed: 'completed',
  running:   'running',
  error:     'error',
}

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant={STATUS_VARIANT[status] ?? 'outline'}>
      {status}
    </Badge>
  )
}

function formatCost(usd: number | null | undefined): string {
  if (usd == null) return '—'
  return usd < 0.0001 ? '<$0.0001' : `$${usd.toFixed(4)}`
}

function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

interface ColDef {
  label: string
  sortKey: string | null
  className?: string
}

const COLUMNS: ColDef[] = [
  { label: 'Agent',    sortKey: 'agent_name' },
  { label: 'Status',   sortKey: 'status' },
  { label: 'Spans',    sortKey: 'span_count' },
  { label: 'Cost',     sortKey: 'total_cost_usd' },
  { label: 'Duration', sortKey: 'duration_ms' },
  { label: 'Created',  sortKey: 'created_at' },
]

function SortIcon({ active, order }: { active: boolean; order: string }) {
  if (!active) {
    return (
      <svg className="inline-block w-3 h-3 ml-1 text-muted-foreground/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4" />
      </svg>
    )
  }
  return order === 'asc' ? (
    <svg className="inline-block w-3 h-3 ml-1 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
    </svg>
  ) : (
    <svg className="inline-block w-3 h-3 ml-1 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  )
}

export function TraceListTable({
  traces,
  onSelect,
  sort = 'created_at',
  order = 'desc',
  onSort,
  compareMode = false,
  selectedIds = [],
  onToggleSelect,
}: Props) {
  if (traces.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground text-sm">
        No traces match your filters.
      </div>
    )
  }

  function handleSort(col: ColDef) {
    if (!col.sortKey || !onSort) return
    onSort(col.sortKey)
  }

  function handleRowClick(t: Trace) {
    if (compareMode && onToggleSelect) {
      onToggleSelect(t.id)
    } else {
      onSelect(t.id)
    }
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          {compareMode && <TableHead className="w-8" />}
          {COLUMNS.map((col) => (
            <TableHead
              key={col.label}
              className={col.sortKey && onSort ? 'cursor-pointer select-none hover:text-foreground transition-colors' : ''}
              onClick={() => handleSort(col)}
            >
              {col.label}
              {col.sortKey && onSort && (
                <SortIcon active={sort === col.sortKey} order={order} />
              )}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {traces.map((t) => {
          const isChecked = selectedIds.includes(t.id)
          const isDisabled = compareMode && selectedIds.length >= 2 && !isChecked
          return (
            <TableRow
              key={t.id}
              onClick={() => handleRowClick(t)}
              className={`cursor-pointer ${isDisabled ? 'opacity-40' : ''}`}
            >
              {compareMode && (
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={isChecked}
                    disabled={isDisabled}
                    onChange={() => onToggleSelect?.(t.id)}
                    className="accent-primary w-3.5 h-3.5 cursor-pointer"
                  />
                </TableCell>
              )}
              <TableCell className="font-mono text-primary text-xs">{t.agent_name}</TableCell>
              <TableCell><StatusBadge status={t.status} /></TableCell>
              <TableCell className="text-foreground/80">{t.span_count}</TableCell>
              <TableCell className="text-foreground/80">{formatCost(t.total_cost_usd)}</TableCell>
              <TableCell className="text-foreground/80">{formatDuration(t.duration_ms)}</TableCell>
              <TableCell className="text-muted-foreground text-xs">{formatDate(t.created_at)}</TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
