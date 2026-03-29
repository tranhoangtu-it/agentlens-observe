/**
 * MCP integration: monkey-patch Client async methods to emit AgentLens spans.
 * Patches callTool, readResource, getPrompt on @modelcontextprotocol/sdk Client.
 */
import { randomUUID } from "node:crypto";
import { ActiveTrace, traceStorage } from "../tracer.js";
import type { SpanData } from "../types.js";

let _patched = false;

/** Extract server name from MCP Client instance. Falls back to "unknown". */
function getServerName(client: unknown): string {
  if (client && typeof client === "object") {
    const info = (client as Record<string, unknown>).serverInfo;
    if (info && typeof info === "object") {
      const name = (info as Record<string, unknown>).name;
      if (typeof name === "string") return name;
    }
  }
  return "unknown";
}

function nowMs(): number {
  return Date.now();
}

function strTruncate(v: unknown, limit: number): string | null {
  if (v == null) return null;
  const s = String(v);
  return s.length > limit ? s.slice(0, limit) : s;
}

function buildSpan(
  active: ActiveTrace,
  name: string,
  type: string,
  startMs: number,
  input: string | null,
  output: string | null,
  metadata: Record<string, unknown>,
): SpanData {
  return {
    span_id: randomUUID(),
    parent_id: active.currentSpanId(),
    name,
    type,
    start_ms: startMs,
    end_ms: nowMs(),
    input,
    output,
    cost: null,
    metadata,
  };
}

function appendSpan(active: ActiveTrace, span: SpanData): void {
  active.spans.push(span);
  active.flushSpan(span);
}

/**
 * Call once at startup to auto-instrument all MCP Client calls.
 * Idempotent — safe to call multiple times.
 *
 * @example
 * ```ts
 * import { patchMcp } from "agentlens/integrations/mcp";
 * patchMcp();
 * ```
 */
export function patchMcp(): void {
  if (_patched) return;

  // Dynamic import to avoid hard dependency on @modelcontextprotocol/sdk
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  let Client: { prototype: Record<string, unknown> };
  try {
    // CommonJS interop — require at runtime so the package stays optional
    // biome-ignore lint/security/noGlobalEval: intentional runtime require
    Client = eval('require')("@modelcontextprotocol/sdk/client/index.js").Client;
  } catch {
    throw new Error(
      "MCP SDK not installed. Run: npm install @modelcontextprotocol/sdk",
    );
  }

  _patchCallTool(Client.prototype);
  _patchReadResource(Client.prototype);
  _patchGetPrompt(Client.prototype);
  _patched = true;
}

function _patchCallTool(proto: Record<string, unknown>): void {
  const original = proto.callTool as (
    ...args: unknown[]
  ) => Promise<unknown>;

  proto.callTool = async function (
    this: unknown,
    params: { name: string; arguments?: unknown },
    ...rest: unknown[]
  ): Promise<unknown> {
    const active = traceStorage.getStore();
    const start = nowMs();
    const result = await original.call(this, params, ...rest);
    if (active) {
      const span = buildSpan(
        active,
        `mcp:${params.name}`,
        "mcp.tool_call",
        start,
        strTruncate(params.arguments, 1024),
        strTruncate(result, 2048),
        {
          mcp_server: getServerName(this),
          tool_name: params.name,
          arguments: params.arguments ?? null,
        },
      );
      appendSpan(active, span);
    }
    return result;
  };
}

function _patchReadResource(proto: Record<string, unknown>): void {
  const original = proto.readResource as (
    ...args: unknown[]
  ) => Promise<unknown>;

  proto.readResource = async function (
    this: unknown,
    params: { uri: string },
    ...rest: unknown[]
  ): Promise<unknown> {
    const active = traceStorage.getStore();
    const start = nowMs();
    const result = await original.call(this, params, ...rest);
    if (active) {
      const uri = params.uri;
      const span = buildSpan(
        active,
        `mcp:read:${uri}`,
        "mcp.resource_read",
        start,
        strTruncate(uri, 1024),
        strTruncate(result, 2048),
        {
          mcp_server: getServerName(this),
          resource_uri: uri,
        },
      );
      appendSpan(active, span);
    }
    return result;
  };
}

function _patchGetPrompt(proto: Record<string, unknown>): void {
  const original = proto.getPrompt as (
    ...args: unknown[]
  ) => Promise<unknown>;

  proto.getPrompt = async function (
    this: unknown,
    params: { name: string; arguments?: unknown },
    ...rest: unknown[]
  ): Promise<unknown> {
    const active = traceStorage.getStore();
    const start = nowMs();
    const result = await original.call(this, params, ...rest);
    if (active) {
      const span = buildSpan(
        active,
        `mcp:prompt:${params.name}`,
        "mcp.prompt_get",
        start,
        strTruncate(params.arguments, 1024),
        strTruncate(result, 2048),
        {
          mcp_server: getServerName(this),
          prompt_name: params.name,
          arguments: params.arguments ?? null,
        },
      );
      appendSpan(active, span);
    }
    return result;
  };
}
