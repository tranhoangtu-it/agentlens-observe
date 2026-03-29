// Autopsy results panel — shows AI analysis of trace failures

import { memo } from 'react'
import { X, AlertTriangle, AlertCircle, Info, RefreshCw, Loader2 } from 'lucide-react'
import { ScrollArea } from './ui/scroll-area'
import type { AutopsyResult } from '../lib/autopsy-api-client'

const SEVERITY_CONFIG = {
  critical: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Critical' },
  warning: { icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', label: 'Warning' },
  info: { icon: Info, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20', label: 'Info' },
} as const

interface AutopsyPanelProps {
  result: AutopsyResult | null
  loading: boolean
  error: string | null
  onClose: () => void
  onRerun: () => void
  onSpanClick?: (spanId: string) => void
}

export const AutopsyPanel = memo(function AutopsyPanel({
  result,
  loading,
  error,
  onClose,
  onRerun,
  onSpanClick,
}: AutopsyPanelProps) {
  const severity = result ? SEVERITY_CONFIG[result.severity] : null
  const SeverityIcon = severity?.icon || Info

  return (
    <aside className="w-96 shrink-0 bg-card border-l border-border flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          AI Autopsy
          {result?.cached && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">cached</span>
          )}
        </h3>
        <div className="flex items-center gap-1">
          {result && (
            <button
              onClick={onRerun}
              className="p-1 text-muted-foreground hover:text-foreground transition-colors"
              title="Re-run analysis"
            >
              <RefreshCw size={13} />
            </button>
          )}
          <button onClick={onClose} className="p-1 text-muted-foreground hover:text-foreground transition-colors">
            <X size={14} />
          </button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="px-4 py-3 space-y-4">
          {/* Loading */}
          {loading && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm py-8 justify-center">
              <Loader2 size={16} className="animate-spin" />
              Analyzing trace with AI...
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-md p-3">
              <p className="text-xs text-red-400">{error}</p>
            </div>
          )}

          {/* Results */}
          {result && !loading && (
            <>
              {/* Severity badge */}
              <div className={`flex items-center gap-2 px-3 py-2 rounded-md ${severity?.bg} border ${severity?.border}`}>
                <SeverityIcon size={14} className={severity?.color} />
                <span className={`text-xs font-medium ${severity?.color}`}>{severity?.label}</span>
              </div>

              {/* Summary */}
              <Section title="Summary">
                <p className="text-sm text-foreground">{result.summary}</p>
              </Section>

              {/* Root cause */}
              <Section title="Root Cause">
                <p className="text-sm text-foreground whitespace-pre-wrap">{result.root_cause}</p>
              </Section>

              {/* Suggested fix */}
              <Section title="Suggested Fix">
                <p className="text-sm text-foreground whitespace-pre-wrap">{result.suggested_fix}</p>
              </Section>

              {/* Affected spans */}
              {result.affected_span_ids.length > 0 && (
                <Section title="Affected Spans">
                  <div className="space-y-1">
                    {result.affected_span_ids.map((id) => (
                      <button
                        key={id}
                        onClick={() => onSpanClick?.(id)}
                        className="block text-xs font-mono text-primary hover:underline truncate max-w-full"
                      >
                        {id}
                      </button>
                    ))}
                  </div>
                </Section>
              )}

              {/* Model info */}
              <div className="text-[10px] text-muted-foreground/60 pt-2 border-t border-border">
                {result.llm_provider}/{result.llm_model} &middot; {new Date(result.created_at).toLocaleString()}
              </div>
            </>
          )}
        </div>
      </ScrollArea>
    </aside>
  )
})

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{title}</h4>
      {children}
    </div>
  )
}
