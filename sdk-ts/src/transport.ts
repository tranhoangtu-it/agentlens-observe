/**
 * Non-blocking HTTP transport. Posts traces/spans to AgentLens server.
 * Uses native fetch (Node 18+). Fire-and-forget — never blocks the caller.
 *
 * Supports two modes:
 * - Immediate: each postTrace/postSpans call fires fetch instantly (default)
 * - Batch: traces are queued and flushed on interval or when queue hits maxSize
 */
import type { SpanData, TracePayload } from "./types.js";

// Module-level server URL — set by Tracer.configure()
let _serverUrl = process.env.AGENTLENS_URL ?? "http://localhost:3000";

// Batch transport state
let _batchEnabled = false;
let _batchQueue: TracePayload[] = [];
let _batchMaxSize = 10;
let _batchFlushInterval = 5000; // ms
let _batchTimer: ReturnType<typeof setTimeout> | null = null;

/** Set the server URL for all transport calls. */
export function setServerUrl(url: string): void {
  _serverUrl = url.replace(/\/+$/, "");
}

/** Get the current server URL. */
export function getServerUrl(): string {
  return _serverUrl;
}

/** Configure batch transport mode. */
export function configureBatch(opts: {
  enabled: boolean;
  serverUrl?: string;
  maxSize?: number;
  flushInterval?: number;
}): void {
  _batchEnabled = opts.enabled;
  if (opts.serverUrl) _serverUrl = opts.serverUrl.replace(/\/+$/, "");
  if (opts.maxSize !== undefined) _batchMaxSize = opts.maxSize;
  if (opts.flushInterval !== undefined) _batchFlushInterval = opts.flushInterval;

  if (_batchEnabled) {
    _scheduleBatchFlush();
  } else {
    _cancelBatchTimer();
  }
}

function _cancelBatchTimer(): void {
  if (_batchTimer !== null) {
    clearTimeout(_batchTimer);
    _batchTimer = null;
  }
}

function _scheduleBatchFlush(): void {
  _cancelBatchTimer();
  if (!_batchEnabled) return;
  _batchTimer = setTimeout(() => flushBatch(), _batchFlushInterval);
  // Allow Node.js to exit even if timer is pending
  if (_batchTimer && typeof _batchTimer === "object" && "unref" in _batchTimer) {
    _batchTimer.unref();
  }
}

/**
 * Flush all queued trace payloads to server.
 * Called automatically by the timer or when queue reaches maxSize.
 * Safe to call manually at program exit.
 */
export function flushBatch(): void {
  if (_batchQueue.length === 0) {
    if (_batchEnabled) _scheduleBatchFlush();
    return;
  }

  const payloads = [..._batchQueue];
  _batchQueue = [];
  const url = `${_serverUrl}/api/traces/batch`;

  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ traces: payloads }),
    signal: AbortSignal.timeout(5000),
  }).catch(() => {
    // fire-and-forget — silently ignore errors
  });

  if (_batchEnabled) _scheduleBatchFlush();
}

/**
 * Fire-and-forget: POST full trace to /api/traces.
 * When batch mode is enabled, queues the trace instead.
 */
export function postTrace(
  traceId: string,
  agentName: string,
  spans: SpanData[],
): void {
  const payload: TracePayload = {
    trace_id: traceId,
    agent_name: agentName,
    spans,
  };

  if (_batchEnabled) {
    _batchQueue.push(payload);
    if (_batchQueue.length >= _batchMaxSize) {
      flushBatch();
    }
    return;
  }

  // Immediate mode
  const url = `${_serverUrl}/api/traces`;
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(5000),
  }).catch(() => {
    // fire-and-forget
  });
}

/**
 * Fire-and-forget incremental: POST spans to /api/traces/{traceId}/spans.
 * Used by streaming mode. Bypasses batch mode intentionally.
 */
export function postSpans(traceId: string, spans: SpanData[]): void {
  const url = `${_serverUrl}/api/traces/${traceId}/spans`;
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spans }),
    signal: AbortSignal.timeout(5000),
  }).catch(() => {
    // fire-and-forget
  });
}

// --- Test helpers (not part of public API) ---

/** Reset batch state. Used by tests only. */
export function _resetBatchState(): void {
  _cancelBatchTimer();
  _batchEnabled = false;
  _batchQueue = [];
  _batchMaxSize = 10;
  _batchFlushInterval = 5000;
  _serverUrl = process.env.AGENTLENS_URL ?? "http://localhost:3000";
}

/** Get current batch queue length. Used by tests only. */
export function _getBatchQueueLength(): number {
  return _batchQueue.length;
}
