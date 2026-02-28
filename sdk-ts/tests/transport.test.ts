import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  _getBatchQueueLength,
  _resetBatchState,
  configureBatch,
  flushBatch,
  postSpans,
  postTrace,
  setServerUrl,
} from "../src/transport.js";
import type { SpanData } from "../src/types.js";

// Mock global fetch
const fetchMock = vi.fn().mockResolvedValue(new Response("ok", { status: 201 }));
vi.stubGlobal("fetch", fetchMock);

function makeSpan(overrides?: Partial<SpanData>): SpanData {
  return {
    span_id: "span-1",
    parent_id: null,
    name: "test",
    type: "tool_call",
    start_ms: 1000,
    end_ms: 2000,
    input: null,
    output: null,
    cost: null,
    metadata: {},
    ...overrides,
  };
}

describe("transport", () => {
  beforeEach(() => {
    fetchMock.mockClear();
    _resetBatchState();
    setServerUrl("http://localhost:3000");
  });

  afterEach(() => {
    _resetBatchState();
  });

  describe("postTrace (immediate mode)", () => {
    it("sends POST to /api/traces with correct payload", () => {
      const span = makeSpan();
      postTrace("trace-1", "TestAgent", [span]);

      expect(fetchMock).toHaveBeenCalledOnce();
      const [url, opts] = fetchMock.mock.calls[0];
      expect(url).toBe("http://localhost:3000/api/traces");
      expect(opts.method).toBe("POST");

      const body = JSON.parse(opts.body);
      expect(body.trace_id).toBe("trace-1");
      expect(body.agent_name).toBe("TestAgent");
      expect(body.spans).toHaveLength(1);
    });

    it("uses custom server URL", () => {
      setServerUrl("http://custom:9000/");
      postTrace("t1", "Agent", [makeSpan()]);

      const [url] = fetchMock.mock.calls[0];
      expect(url).toBe("http://custom:9000/api/traces");
    });
  });

  describe("postSpans", () => {
    it("sends POST to /api/traces/{id}/spans", () => {
      const span = makeSpan();
      postSpans("trace-42", [span]);

      expect(fetchMock).toHaveBeenCalledOnce();
      const [url, opts] = fetchMock.mock.calls[0];
      expect(url).toBe("http://localhost:3000/api/traces/trace-42/spans");

      const body = JSON.parse(opts.body);
      expect(body.spans).toHaveLength(1);
    });
  });

  describe("batch mode", () => {
    it("queues traces when batch enabled", () => {
      configureBatch({ enabled: true, maxSize: 5, flushInterval: 60000 });

      postTrace("t1", "Agent", [makeSpan()]);
      postTrace("t2", "Agent", [makeSpan()]);

      // Should NOT have called fetch yet (queued)
      expect(fetchMock).not.toHaveBeenCalled();
      expect(_getBatchQueueLength()).toBe(2);
    });

    it("auto-flushes when queue reaches maxSize", () => {
      configureBatch({ enabled: true, maxSize: 2, flushInterval: 60000 });

      postTrace("t1", "Agent", [makeSpan()]);
      expect(fetchMock).not.toHaveBeenCalled();

      postTrace("t2", "Agent", [makeSpan()]);
      // Should flush now (maxSize reached)
      expect(fetchMock).toHaveBeenCalledOnce();

      const [url, opts] = fetchMock.mock.calls[0];
      expect(url).toBe("http://localhost:3000/api/traces/batch");
      const body = JSON.parse(opts.body);
      expect(body.traces).toHaveLength(2);
    });

    it("flushBatch sends all queued traces", () => {
      configureBatch({ enabled: true, maxSize: 100, flushInterval: 60000 });

      postTrace("t1", "Agent", [makeSpan()]);
      postTrace("t2", "Agent", [makeSpan()]);
      postTrace("t3", "Agent", [makeSpan()]);

      flushBatch();
      expect(fetchMock).toHaveBeenCalledOnce();

      const body = JSON.parse(fetchMock.mock.calls[0][1].body);
      expect(body.traces).toHaveLength(3);
      expect(_getBatchQueueLength()).toBe(0);
    });

    it("flushBatch does nothing when queue is empty", () => {
      configureBatch({ enabled: true, maxSize: 100, flushInterval: 60000 });
      flushBatch();
      expect(fetchMock).not.toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("silently ignores fetch errors", () => {
      fetchMock.mockRejectedValueOnce(new Error("network error"));
      // Should not throw
      expect(() => postTrace("t1", "Agent", [makeSpan()])).not.toThrow();
    });
  });
});
