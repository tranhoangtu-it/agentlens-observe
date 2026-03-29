/**
 * Core tracing logic: Tracer, ActiveTrace, SpanContext, context management.
 * Uses AsyncLocalStorage (Node 18+) for context propagation across async boundaries.
 */
import { AsyncLocalStorage } from "node:async_hooks";
import { randomUUID } from "node:crypto";
import { calculateCost } from "./cost.js";
import {
  configureBatch,
  postSpans,
  postTrace,
  setServerUrl,
} from "./transport.js";
import type {
  CostData,
  ISpanContext,
  LogEntry,
  SpanData,
  SpanExporter,
  TracerConfig,
} from "./types.js";

// --- Helpers ---

function nowMs(): number {
  return Date.now();
}

function strTruncate(v: unknown, limit = 4096): string | null {
  if (v == null) return null;
  const s = String(v);
  return s.length > limit ? s.slice(0, limit) : s;
}

// --- Context storage ---

export const traceStorage = new AsyncLocalStorage<ActiveTrace>();

// Global list of registered exporters
const exporters: SpanExporter[] = [];

function emitToExporters(span: SpanData): void {
  for (const exporter of exporters) {
    try {
      exporter.exportSpan(span);
    } catch {
      // non-fatal — never let exporters crash the app
    }
  }
}

// --- ActiveTrace ---

export class ActiveTrace {
  readonly traceId: string;
  readonly agentName: string;
  readonly streaming: boolean;
  readonly spans: SpanData[] = [];
  private readonly spanStack: string[] = [];

  constructor(traceId: string, agentName: string, streaming = false) {
    this.traceId = traceId;
    this.agentName = agentName;
    this.streaming = streaming;
  }

  currentSpanId(): string | null {
    return this.spanStack.length > 0
      ? this.spanStack[this.spanStack.length - 1]
      : null;
  }

  pushSpan(span: SpanData): void {
    this.spans.push(span);
    this.spanStack.push(span.span_id);
  }

  popSpan(): void {
    this.spanStack.pop();
  }

  /** Send a single completed span immediately (streaming mode only). */
  flushSpan(span: SpanData): void {
    emitToExporters(span);
    if (this.streaming) {
      postSpans(this.traceId, [span]);
    }
  }

  /** Send the full trace batch. */
  flush(): void {
    for (const span of this.spans) {
      emitToExporters(span);
    }
    postTrace(this.traceId, this.agentName, this.spans);
  }
}

// --- SpanContext ---

export class SpanContext {
  private readonly active: ActiveTrace;
  private readonly span: SpanData;
  private entered = false;

  constructor(active: ActiveTrace, span: SpanData) {
    this.active = active;
    this.span = span;
  }

  setOutput(output: string): void {
    this.span.output = strTruncate(output);
  }

  setCost(
    model: string,
    opts: { inputTokens: number; outputTokens: number; usd?: number },
  ): void {
    const cost: CostData = {
      model,
      input_tokens: opts.inputTokens,
      output_tokens: opts.outputTokens,
      usd:
        opts.usd ??
        calculateCost(model, opts.inputTokens, opts.outputTokens),
    };
    this.span.cost = cost;
  }

  setMetadata(data: Record<string, unknown>): void {
    Object.assign(this.span.metadata, data);
  }

  log(message: string, extra?: Record<string, unknown>): void {
    const logs = (this.span.metadata.logs ??= []) as LogEntry[];
    const entry: LogEntry = {
      ts_ms: nowMs(),
      message: String(message).slice(0, 1024),
    };
    if (extra) Object.assign(entry, extra);
    logs.push(entry);
  }

  /** Enter this span context (push onto stack). */
  enter(): this {
    this.active.pushSpan(this.span);
    this.entered = true;
    return this;
  }

  /** Exit this span context (pop from stack, flush in streaming mode). */
  exit(): void {
    if (!this.entered) return;
    this.span.end_ms = nowMs();
    this.active.popSpan();
    this.active.flushSpan(this.span);
    this.entered = false;
  }
}

// --- NoopSpanContext (when span() called outside a trace) ---

class NoopSpanContext {
  setOutput(): void {}
  setCost(): void {}
  setMetadata(): void {}
  log(): void {}
  enter(): this {
    return this;
  }
  exit(): void {}
}

// --- Tracer ---

export class Tracer {
  private serverUrl: string | null = null;
  private streaming = false;

  configure(config: TracerConfig): void {
    this.serverUrl = config.serverUrl;
    this.streaming = config.streaming ?? false;
    setServerUrl(config.serverUrl);

    if (config.batch) {
      configureBatch({
        enabled: true,
        serverUrl: config.serverUrl,
        maxSize: config.batchMaxSize,
        flushInterval: config.batchFlushInterval,
      });
    }
  }

  addExporter(exporter: SpanExporter): void {
    exporters.push(exporter);
  }

  /**
   * Execute a function within a trace context.
   * Unlike Python's decorator approach, this uses a higher-order function
   * since TypeScript decorators are experimental.
   *
   * Usage:
   *   const result = await agentlens.trace("MyAgent", async () => { ... });
   */
  trace<T>(
    agentName: string,
    fn: () => T | Promise<T>,
    opts?: { spanType?: string; input?: string },
  ): T | Promise<T> {
    const spanType = opts?.spanType ?? "agent_run";
    const active = new ActiveTrace(
      randomUUID(),
      agentName,
      this.streaming,
    );
    const root: SpanData = {
      span_id: randomUUID(),
      parent_id: null,
      name: agentName,
      type: spanType,
      start_ms: nowMs(),
      end_ms: null,
      input: strTruncate(opts?.input),
      output: null,
      cost: null,
      metadata: {},
    };
    active.pushSpan(root);

    // Detect if fn returns a promise
    let result: T | Promise<T>;
    try {
      result = traceStorage.run(active, fn);
    } catch (err) {
      root.metadata.error = String(err);
      root.end_ms = nowMs();
      active.popSpan();
      active.flush();
      throw err;
    }

    // Handle async case
    if (result instanceof Promise) {
      return result.then(
        (val) => {
          root.output = strTruncate(val);
          root.end_ms = nowMs();
          active.popSpan();
          active.flush();
          return val;
        },
        (err) => {
          root.metadata.error = String(err);
          root.end_ms = nowMs();
          active.popSpan();
          active.flush();
          throw err;
        },
      );
    }

    // Sync case
    root.output = strTruncate(result);
    root.end_ms = nowMs();
    active.popSpan();
    active.flush();
    return result;
  }

  /** Create a child span context. Returns NoopSpanContext when called outside a trace. */
  span(name: string, spanType = "tool_call"): ISpanContext {
    const active = traceStorage.getStore();
    if (!active) return new NoopSpanContext();

    const s: SpanData = {
      span_id: randomUUID(),
      parent_id: active.currentSpanId(),
      name,
      type: spanType,
      start_ms: nowMs(),
      end_ms: null,
      input: null,
      output: null,
      cost: null,
      metadata: {},
    };
    return new SpanContext(active, s);
  }

  /** Add a timestamped log to the current active span. No-ops outside a trace. */
  log(message: string, extra?: Record<string, unknown>): void {
    const active = traceStorage.getStore();
    if (!active) return;

    const spanId = active.currentSpanId();
    if (!spanId) return;

    // Find innermost span on the stack
    for (let i = active.spans.length - 1; i >= 0; i--) {
      if (active.spans[i].span_id === spanId) {
        const logs = (active.spans[i].metadata.logs ??= []) as LogEntry[];
        const entry: LogEntry = {
          ts_ms: nowMs(),
          message: String(message).slice(0, 1024),
        };
        if (extra) Object.assign(entry, extra);
        logs.push(entry);
        return;
      }
    }
  }

  /** Get the current active trace, if any. */
  currentTrace(): ActiveTrace | undefined {
    return traceStorage.getStore();
  }
}
