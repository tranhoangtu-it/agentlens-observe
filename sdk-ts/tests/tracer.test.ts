import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { configure, trace, span, log, currentTrace, addExporter } from "../src/index.js";
import type { SpanData, SpanExporter } from "../src/types.js";

// Mock fetch globally so transport doesn't actually send
const fetchMock = vi.fn().mockResolvedValue(new Response("ok", { status: 201 }));
vi.stubGlobal("fetch", fetchMock);

describe("Tracer", () => {
  beforeEach(() => {
    fetchMock.mockClear();
    configure({ serverUrl: "http://localhost:3000" });
  });

  describe("trace()", () => {
    it("executes sync function and returns result", () => {
      const result = trace("TestAgent", () => "hello");
      expect(result).toBe("hello");
    });

    it("executes async function and returns result", async () => {
      const result = await trace("AsyncAgent", async () => {
        return "async-result";
      });
      expect(result).toBe("async-result");
    });

    it("propagates sync errors", () => {
      expect(() =>
        trace("ErrorAgent", () => {
          throw new Error("test error");
        }),
      ).toThrow("test error");
    });

    it("propagates async errors", async () => {
      await expect(
        trace("ErrorAgent", async () => {
          throw new Error("async error");
        }),
      ).rejects.toThrow("async error");
    });

    it("sends trace to server via fetch", () => {
      fetchMock.mockClear();

      trace("PostAgent", () => "result");

      // postTrace fires fetch
      expect(fetchMock).toHaveBeenCalledOnce();
      const [url, opts] = fetchMock.mock.calls[0];
      expect(url).toBe("http://localhost:3000/api/traces");
      const body = JSON.parse(opts!.body as string);
      expect(body.agent_name).toBe("PostAgent");
      expect(body.spans).toHaveLength(1);
      expect(body.spans[0].name).toBe("PostAgent");
      expect(body.spans[0].type).toBe("agent_run");
    });
  });

  describe("span()", () => {
    it("creates child spans within a trace", () => {
      fetchMock.mockClear();

      trace("SpanAgent", () => {
        const s = span("search", "tool_call").enter();
        s.setOutput("found 3 results");
        s.setCost("gpt-4o", { inputTokens: 500, outputTokens: 200 });
        s.exit();
      });

      const body = JSON.parse(fetchMock.mock.calls[0][1]!.body as string);
      expect(body.spans).toHaveLength(2); // root + child

      const childSpan = body.spans[1];
      expect(childSpan.name).toBe("search");
      expect(childSpan.type).toBe("tool_call");
      expect(childSpan.output).toBe("found 3 results");
      expect(childSpan.cost.model).toBe("gpt-4o");
      expect(childSpan.cost.input_tokens).toBe(500);
      expect(childSpan.cost.output_tokens).toBe(200);
      expect(childSpan.cost.usd).toBeGreaterThan(0);

      // Parent relationship
      const rootSpan = body.spans[0];
      expect(childSpan.parent_id).toBe(rootSpan.span_id);
    });

    it("supports nested spans", () => {
      fetchMock.mockClear();

      trace("NestedAgent", () => {
        const outer = span("outer", "tool_call").enter();

        const inner = span("inner", "llm_call").enter();
        inner.setOutput("inner result");
        inner.exit();

        outer.setOutput("outer result");
        outer.exit();
      });

      const body = JSON.parse(fetchMock.mock.calls[0][1]!.body as string);
      expect(body.spans).toHaveLength(3); // root + outer + inner

      const [root, outerSpan, innerSpan] = body.spans;
      expect(outerSpan.parent_id).toBe(root.span_id);
      expect(innerSpan.parent_id).toBe(outerSpan.span_id);
    });

    it("returns noop context outside a trace", () => {
      const s = span("orphan");
      // Should not throw
      s.enter();
      s.setOutput("test");
      s.exit();
    });
  });

  describe("log()", () => {
    it("adds log entries to current span metadata", () => {
      fetchMock.mockClear();

      trace("LogAgent", () => {
        const s = span("work").enter();
        log("starting work", { phase: "init" });
        s.exit();
      });

      const body = JSON.parse(fetchMock.mock.calls[0][1]!.body as string);
      // Log should be on the "work" span (innermost on stack when log() was called)
      const workSpan = body.spans.find((s: SpanData) => s.name === "work");
      expect(workSpan.metadata.logs).toHaveLength(1);
      expect(workSpan.metadata.logs[0].message).toBe("starting work");
      expect(workSpan.metadata.logs[0].phase).toBe("init");
      expect(workSpan.metadata.logs[0].ts_ms).toBeTypeOf("number");
    });

    it("no-ops outside a trace", () => {
      // Should not throw
      log("orphan log");
    });
  });

  describe("currentTrace()", () => {
    it("returns undefined outside a trace", () => {
      expect(currentTrace()).toBeUndefined();
    });

    it("returns ActiveTrace inside a trace", () => {
      trace("CtxAgent", () => {
        const active = currentTrace();
        expect(active).toBeDefined();
        expect(active!.agentName).toBe("CtxAgent");
      });
    });
  });

  describe("async context isolation", () => {
    it("maintains separate contexts for concurrent traces", async () => {
      fetchMock.mockClear();

      const p1 = trace("Agent1", async () => {
        await new Promise((r) => setTimeout(r, 10));
        const s = span("span1").enter();
        s.setOutput("from agent1");
        s.exit();
        return "result1";
      });

      const p2 = trace("Agent2", async () => {
        const s = span("span2").enter();
        s.setOutput("from agent2");
        s.exit();
        return "result2";
      });

      const [r1, r2] = await Promise.all([p1, p2]);
      expect(r1).toBe("result1");
      expect(r2).toBe("result2");

      // Both traces should have been sent
      expect(fetchMock.mock.calls.length).toBe(2);

      // Verify each trace has its own spans (not mixed)
      const bodies = fetchMock.mock.calls.map(([, opts]) =>
        JSON.parse(opts!.body as string),
      );
      const agent1Body = bodies.find((b) => b.agent_name === "Agent1");
      const agent2Body = bodies.find((b) => b.agent_name === "Agent2");

      expect(agent1Body).toBeDefined();
      expect(agent2Body).toBeDefined();

      // Agent1 has root + span1, Agent2 has root + span2
      const a1Spans = agent1Body.spans.map((s: SpanData) => s.name);
      const a2Spans = agent2Body.spans.map((s: SpanData) => s.name);

      expect(a1Spans).toContain("span1");
      expect(a1Spans).not.toContain("span2");
      expect(a2Spans).toContain("span2");
      expect(a2Spans).not.toContain("span1");
    });
  });

  describe("addExporter()", () => {
    it("calls exporter for each span", () => {
      const exported: SpanData[] = [];
      const exporter: SpanExporter = {
        exportSpan: (s) => exported.push(s),
        shutdown: () => {},
      };
      addExporter(exporter);

      trace("ExportAgent", () => {
        const s = span("child").enter();
        s.exit();
      });

      // root span + child span exported
      expect(exported.length).toBeGreaterThanOrEqual(2);
      expect(exported.some((s) => s.name === "ExportAgent")).toBe(true);
      expect(exported.some((s) => s.name === "child")).toBe(true);
    });
  });
});
