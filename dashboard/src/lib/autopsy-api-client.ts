// API client for AI-powered failure autopsy

import { fetchWithAuth } from './fetch-with-auth'

const BASE = '/api'

export interface AutopsyResult {
  id: string
  trace_id: string
  root_cause: string
  summary: string
  severity: 'critical' | 'warning' | 'info'
  suggested_fix: string
  affected_span_ids: string[]
  llm_provider: string
  llm_model: string
  created_at: string
  cached: boolean
}

export interface AutopsyRequest {
  provider?: string
  model?: string
}

export async function triggerAutopsy(
  traceId: string,
  opts?: AutopsyRequest,
): Promise<AutopsyResult> {
  const res = await fetchWithAuth(`${BASE}/traces/${traceId}/autopsy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts ?? {}),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Autopsy failed' }))
    throw new Error(err.detail || `Autopsy failed: ${res.status}`)
  }
  return res.json()
}

export async function fetchAutopsy(traceId: string): Promise<AutopsyResult | null> {
  const res = await fetchWithAuth(`${BASE}/traces/${traceId}/autopsy`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`fetchAutopsy failed: ${res.status}`)
  return res.json()
}

export async function deleteAutopsy(traceId: string): Promise<void> {
  const res = await fetchWithAuth(`${BASE}/traces/${traceId}/autopsy`, {
    method: 'DELETE',
  })
  if (!res.ok && res.status !== 404) throw new Error(`deleteAutopsy failed: ${res.status}`)
}
