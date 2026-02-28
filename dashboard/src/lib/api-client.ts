// API client for AgentLens backend — typed fetch wrappers for traces/spans

export interface Trace {
  id: string
  agent_name: string
  created_at: string
  total_cost_usd: number
  total_tokens: number
  span_count: number
  duration_ms: number
  status: 'completed' | 'running' | 'error'
}

export interface Span {
  id: string
  trace_id: string
  parent_id: string | null
  name: string
  type: 'agent_run' | 'tool_call' | 'llm_call' | 'handoff' | string
  start_ms: number
  end_ms: number
  input: unknown
  output: unknown
  cost_model: string | null
  cost_input_tokens: number
  cost_output_tokens: number
  cost_usd: number
}

export interface TracesResponse {
  traces: Trace[]
  count: number
}

export interface TraceDetailResponse {
  trace: Trace
  spans: Span[]
}

const BASE = '/api'

export async function fetchTraces(agentName?: string): Promise<TracesResponse> {
  const url = agentName
    ? `${BASE}/traces?agent_name=${encodeURIComponent(agentName)}`
    : `${BASE}/traces`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`fetchTraces failed: ${res.status}`)
  return res.json() as Promise<TracesResponse>
}

export async function fetchTrace(id: string): Promise<TraceDetailResponse> {
  const res = await fetch(`${BASE}/traces/${encodeURIComponent(id)}`)
  if (!res.ok) throw new Error(`fetchTrace failed: ${res.status}`)
  return res.json() as Promise<TraceDetailResponse>
}
