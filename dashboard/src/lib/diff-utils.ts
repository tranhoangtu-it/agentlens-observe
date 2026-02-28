// diff-utils.ts — simple line-by-line text diff for span input/output comparison
// No external library needed: split by newline, compare line sets via LCS-lite approach

export type DiffLineType = 'added' | 'removed' | 'unchanged'

export interface DiffLine {
  type: DiffLineType
  text: string
}

/**
 * Compute a simple line-diff between two text values.
 * Uses a greedy LCS approach: good enough for agent input/output diffs.
 * Truncates each side to MAX_CHARS before diffing for performance.
 */
const MAX_CHARS = 4096

export function diffText(left: string, right: string): DiffLine[] {
  const l = left.slice(0, MAX_CHARS)
  const r = right.slice(0, MAX_CHARS)

  if (l === r) {
    return l.split('\n').map((text) => ({ type: 'unchanged', text }))
  }

  const leftLines = l.split('\n')
  const rightLines = r.split('\n')

  // Build LCS table (length only)
  const m = leftLines.length
  const n = rightLines.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (leftLines[i - 1] === rightLines[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
      }
    }
  }

  // Traceback to build diff
  const result: DiffLine[] = []
  let i = m
  let j = n

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && leftLines[i - 1] === rightLines[j - 1]) {
      result.unshift({ type: 'unchanged', text: leftLines[i - 1] })
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.unshift({ type: 'added', text: rightLines[j - 1] })
      j--
    } else {
      result.unshift({ type: 'removed', text: leftLines[i - 1] })
      i--
    }
  }

  return result
}

/** Format a numeric delta with sign and optional unit. */
export function formatDelta(
  delta: number | null | undefined,
  formatter: (v: number) => string,
): string {
  if (delta == null) return '—'
  const sign = delta > 0 ? '+' : ''
  return `${sign}${formatter(delta)}`
}

export function formatCostDelta(delta: number | null | undefined): string {
  return formatDelta(delta, (v) => `$${Math.abs(v) < 0.0001 ? '<0.0001' : v.toFixed(4)}`)
}

export function formatDurationDelta(delta: number | null | undefined): string {
  return formatDelta(delta, (v) => (Math.abs(v) < 1000 ? `${v}ms` : `${(v / 1000).toFixed(2)}s`))
}

export function formatTokenDelta(delta: number | null | undefined): string {
  return formatDelta(delta, (v) => `${v}`)
}

/** Percentage change string, e.g. "+200%" */
export function formatPctChange(from: number | null | undefined, to: number | null | undefined): string {
  if (from == null || to == null || from === 0) return ''
  const pct = ((to - from) / Math.abs(from)) * 100
  const sign = pct > 0 ? '+' : ''
  return ` (${sign}${pct.toFixed(0)}%)`
}
