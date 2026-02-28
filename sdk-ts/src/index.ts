/**
 * AgentLens TypeScript SDK — trace AI agents visually.
 * Public API: configure, trace, span, log, addExporter, currentTrace.
 */
export { calculateCost } from "./cost.js";
export { Tracer, ActiveTrace, SpanContext } from "./tracer.js";
export { flushBatch, postSpans, postTrace } from "./transport.js";
export type {
  CostData,
  ISpanContext,
  LogEntry,
  SpanData,
  SpanExporter,
  SpansPayload,
  TracerConfig,
  TracePayload,
} from "./types.js";

import { Tracer } from "./tracer.js";
import type { ISpanContext, TracerConfig, SpanExporter } from "./types.js";

// Singleton tracer instance
const _tracer = new Tracer();

/** Configure the AgentLens server URL and transport options. */
export function configure(config: TracerConfig): void {
  _tracer.configure(config);
}

/**
 * Execute a function within a trace context.
 *
 * @example
 * ```ts
 * const result = await agentlens.trace("MyAgent", async () => {
 *   const s = agentlens.span("search", "tool_call").enter();
 *   s.setOutput("found 5 results");
 *   s.setCost("gpt-4o", { inputTokens: 500, outputTokens: 200 });
 *   s.exit();
 *   return "done";
 * });
 * ```
 */
export function trace<T>(
  agentName: string,
  fn: () => T | Promise<T>,
  opts?: { spanType?: string; input?: string },
): T | Promise<T> {
  return _tracer.trace(agentName, fn, opts);
}

/** Create a child span. Call .enter() to start, .exit() to end. */
export function span(name: string, spanType?: string): ISpanContext {
  return _tracer.span(name, spanType);
}

/** Add a timestamped log to the current active span. */
export function log(message: string, extra?: Record<string, unknown>): void {
  _tracer.log(message, extra);
}

/** Register an optional span exporter (e.g. OpenTelemetry). */
export function addExporter(exporter: SpanExporter): void {
  _tracer.addExporter(exporter);
}

/** Get the current active trace, if any. */
export function currentTrace() {
  return _tracer.currentTrace();
}
