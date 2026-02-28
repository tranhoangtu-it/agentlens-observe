/**
 * Core type definitions for the AgentLens TypeScript SDK.
 * Mirrors Python SDK dataclasses and server request schemas.
 */

/** Cost data for an LLM call within a span. */
export interface CostData {
  model: string;
  input_tokens: number;
  output_tokens: number;
  usd: number | null;
}

/** A single span representing an operation within a trace. */
export interface SpanData {
  span_id: string;
  parent_id: string | null;
  name: string;
  type: string;
  start_ms: number;
  end_ms: number | null;
  input: string | null;
  output: string | null;
  cost: CostData | null;
  metadata: Record<string, unknown>;
}

/** Configuration options for the Tracer. */
export interface TracerConfig {
  /** Base URL of the AgentLens server (e.g. "http://localhost:3000"). */
  serverUrl: string;
  /**
   * When true, completed spans are sent immediately as they finish
   * rather than waiting for the full trace to complete.
   */
  streaming?: boolean;
  /** When true, traces are queued and flushed in batches. */
  batch?: boolean;
  /** Flush batch when this many traces accumulate. Default: 10. */
  batchMaxSize?: number;
  /** Auto-flush batch every N milliseconds. Default: 5000. */
  batchFlushInterval?: number;
}

/** Protocol for optional span exporters (e.g. OpenTelemetry). */
export interface SpanExporter {
  /** Called after each span completes. Must not throw. */
  exportSpan(spanData: SpanData): void;
  /** Called when the process is done. Flush any pending state. */
  shutdown(): void;
}

/** Payload sent to POST /api/traces. */
export interface TracePayload {
  trace_id: string;
  agent_name: string;
  spans: SpanData[];
}

/** Payload sent to POST /api/traces/{id}/spans. */
export interface SpansPayload {
  spans: SpanData[];
}

/**
 * Interface for span context objects returned by span().
 * Both SpanContext (inside trace) and NoopSpanContext (outside trace) implement this.
 */
export interface ISpanContext {
  setOutput(output: string): void;
  setCost(
    model: string,
    opts: { inputTokens: number; outputTokens: number; usd?: number },
  ): void;
  setMetadata(data: Record<string, unknown>): void;
  log(message: string, extra?: Record<string, unknown>): void;
  enter(): this;
  exit(): void;
}

/** Log entry stored in span metadata. */
export interface LogEntry {
  ts_ms: number;
  message: string;
  [key: string]: unknown;
}
