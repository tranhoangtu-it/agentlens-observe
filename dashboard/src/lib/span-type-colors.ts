// Shared span type → hex color mapping
// Used by TraceTopologyGraph and ReplayTimelineScrubber
export const SPAN_TYPE_COLORS: Record<string, string> = {
  agent_run: '#3b82f6', // blue-500
  tool_call: '#22c55e', // green-500
  llm_call:  '#a855f7', // purple-500
  handoff:   '#f97316', // orange-500
}

export const DEFAULT_SPAN_COLOR = '#6b7280'
