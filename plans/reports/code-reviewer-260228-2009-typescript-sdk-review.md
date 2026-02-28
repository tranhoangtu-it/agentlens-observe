# Code Review — AgentLens TypeScript SDK

**Date:** 2026-02-28
**Reviewer:** code-reviewer
**Scope:** sdk-ts full source — 5 source files, 3 test files, 2 config files

---

## Scope

- Files: `src/types.ts`, `src/cost.ts`, `src/transport.ts`, `src/tracer.ts`, `src/index.ts`, `tests/*.test.ts`, `package.json`, `tsconfig.json`, `tsup.config.ts`
- LOC: ~600 source, ~340 tests
- Tests: 30/30 pass, typecheck clean, build succeeds
- Scout findings: see "Edge Cases" section below

---

## Overall Assessment

Solid port of the Python SDK. Code is clean, readable, well-commented, and idiomatic TypeScript. No critical security issues. The primary concerns are: (1) API divergence from Python SDK in two places, (2) a missing `tsup` split-chunk config for CJS/ESM interop, (3) module-level mutable globals in transport create hidden state between tests that `_resetBatchState` only partially addresses, and (4) a few medium-priority type-safety gaps.

---

## Critical Issues

None.

---

## High Priority

### H1 — `setCost` API signature mismatch vs Python SDK

**File:** `src/tracer.ts` line 114, `src/index.ts` line 37

**Problem:** Python `set_cost(model, input_tokens, output_tokens, usd=None)` takes positional args. TypeScript port uses a named-object second arg `{ inputTokens, outputTokens, usd? }`. This is fine ergonomically, but the exporter protocol also diverges: Python uses `export_span` (snake_case), TypeScript uses `exportSpan` (camelCase). The protocol docstring in `types.ts` says "Mirrors Python SDK" but does not note the naming divergence. Consumers porting Python exporter code will be silently broken.

**Fix:** Add a comment in `types.ts` and `tracer.ts` noting the intentional API differences. Consider exporting a mapping table or migration note in README so SDK consumers know what changed.

### H2 — `strTruncate` returns `string | null` but `SpanData.input/output` typing allows `string | null` correctly; however root span `input` is never populated

**File:** `src/tracer.ts` lines 217-228

**Problem:** Python `_run_sync` captures `args[0] if args else kwargs` into `root.input`. The TypeScript `trace()` function never populates `root.input` (always `null`). This is a feature gap — the server-side trace will show no input for the root span when using the TS SDK.

**Fix:**
```ts
trace<T>(
  agentName: string,
  fn: () => T | Promise<T>,
  opts?: { spanType?: string; input?: string },
): T | Promise<T> {
  // ...
  const root: SpanData = {
    // ...
    input: opts?.input ?? null,
    // ...
  };
```
Allow callers to pass input explicitly since TS can't auto-capture args like Python.

### H3 — `_serverUrl` module-level global is not reset between tests

**File:** `src/transport.ts` line 12

**Problem:** `_resetBatchState()` does NOT reset `_serverUrl`. If one test calls `setServerUrl("http://custom:9000")`, a subsequent test relying on the default URL will see the wrong URL. The test for `postTrace (immediate mode)` calls `setServerUrl("http://localhost:3000")` explicitly in `beforeEach` — this masks the issue. If a test were added that called `postTrace` without a prior `setServerUrl`, it could see stale state from another test file or test order.

**Fix:** Add `_serverUrl = "http://localhost:3000"` inside `_resetBatchState()`:
```ts
export function _resetBatchState(): void {
  _cancelBatchTimer();
  _batchEnabled = false;
  _batchQueue = [];
  _batchMaxSize = 10;
  _batchFlushInterval = 5000;
  _serverUrl = process.env.AGENTLENS_URL ?? "http://localhost:3000"; // add this
}
```

---

## Medium Priority

### M1 — `Tracer.streaming` property is instance-level but `exporters` array is module-level (global singleton leak)

**File:** `src/tracer.ts` lines 39, 194

**Problem:** `exporters` is a module-level array, not a property of `Tracer`. `addExporter()` on the singleton `_tracer` in `index.ts` accumulates exporters across the test suite — the `addExporter` test adds an exporter that persists for all subsequent tests. This is the reason the test asserts `exported.length >= 2` (not exactly 2). In production this is fine (single process, single tracer), but it makes tests order-dependent and can cause ghost exports.

**Fix:** Move `exporters` inside the `Tracer` class:
```ts
class Tracer {
  private readonly exporters: SpanExporter[] = [];
  // ...
  addExporter(exporter: SpanExporter): void {
    this.exporters.push(exporter);
  }
}
```
This also makes it easier to have multiple `Tracer` instances in tests without shared state.

### M2 — `NoopSpanContext` not exported; users can't type-annotate span variables cleanly

**File:** `src/tracer.ts` line 162, `src/index.ts` line 52

**Problem:** `span()` returns `SpanContext | NoopSpanContext` but `NoopSpanContext` is a private class. Users who want to annotate a variable with the return type of `span()` cannot:
```ts
const s: ??? = agentlens.span("x"); // can't type this
```

**Fix options:**
1. Export `NoopSpanContext` (simplest).
2. Extract a shared `ISpanContext` interface that both implement and export that as the return type.

Option 2 is cleaner:
```ts
// types.ts
export interface ISpanContext {
  setOutput(output: string): void;
  setCost(model: string, opts: { inputTokens: number; outputTokens: number; usd?: number }): void;
  setMetadata(data: Record<string, unknown>): void;
  log(message: string, extra?: Record<string, unknown>): void;
  enter(): this;
  exit(): void;
}
```
Then `span()` returns `ISpanContext`.

### M3 — `tsconfig.json` excludes `tests/` but vitest runs tests via `ts-node`/`vite` directly; `lib` array missing `DOM` which is needed for `fetch`/`Response`

**File:** `tsconfig.json` line 6

**Problem:** `"lib": ["ES2022"]` does not include `"DOM"` or `"DOM.Iterable"`, meaning the `fetch`, `Response`, `AbortSignal` globals used in `transport.ts` are only resolved because `@types/node` has some partial `fetch` types (Node 18 polyfill types). If the lib is ever changed or if `@types/node` version changes, these types could break.

**Fix:**
```json
"lib": ["ES2022", "DOM"]
```
Or alternatively add `"lib.dom.d.ts"` ref. Since this is a Node-only SDK using Node 18's built-in fetch, adding a `/// <reference types="..." />` comment in `transport.ts` is an acceptable alternative.

### M4 — `configureBatch` in transport: timer reschedule after `flushBatch` is called inside `postTrace` (potential double-schedule)

**File:** `src/transport.ts` lines 87-92

**Problem:** When `postTrace` triggers `flushBatch()` via maxSize flush, `flushBatch` calls `_scheduleBatchFlush()` at line 91. But `configureBatch` also calls `_scheduleBatchFlush()` at line 44. If `configureBatch` is called again mid-run (e.g. reconfigure), the timer can double-schedule. The `_cancelBatchTimer()` at the top of `_scheduleBatchFlush` prevents most cases, but the `configureBatch` path also calls `_scheduleBatchFlush()` without cancellation guard when a timer is already running from a prior `flushBatch` reschedule.

This is low-risk in practice (Node timer deduplication via cancel works), but the interleaving in `flushBatch` → `_scheduleBatchFlush` → `_cancelBatchTimer` → new `setTimeout` can create a split-second window where two timers co-exist.

**Fix:** Simplify by always cancelling inside `_scheduleBatchFlush` (already done) and removing the duplicate cancel call inside `configureBatch`:
```ts
// configureBatch: let _scheduleBatchFlush handle cancel
if (_batchEnabled) {
  _scheduleBatchFlush();  // this cancels existing timer internally
} else {
  _cancelBatchTimer();
}
```
Current code is actually correct — the issue is theoretical. Low practical impact.

### M5 — `package.json` missing `repository`, `homepage`, `author` fields; version is `0.1.0` while Python SDK is `0.2.0` / PyPI package is `0.3.0`

**File:** `package.json`

**Problem:** Published npm packages without `repository` field lose GitHub linking on npmjs.com. Version `0.1.0` will cause confusion against the PyPI `0.3.0` tag. Consider aligning to a `0.1.0` namespace separately or documenting the divergence.

**Fix:**
```json
{
  "version": "0.1.0",
  "repository": { "type": "git", "url": "https://github.com/tranhoangtu-it/agentlens" },
  "homepage": "https://github.com/tranhoangtu-it/agentlens/tree/main/sdk-ts",
  "author": "..."
}
```

---

## Low Priority

### L1 — `nowMs()` returns `number` (float), Python `_now_ms()` returns `int`

**File:** `src/tracer.ts` line 24

`Date.now()` in JavaScript always returns an integer ms value (no fractional part), so this is safe. But `SpanData.start_ms` / `end_ms` typed as `number` is correct. No action needed — just note the type docs could say "integer milliseconds".

### L2 — `calculateCost` rounds to 6 decimal places via `Math.round(usd * 1e6) / 1e6`, Python uses `round(usd, 6)` — equivalent but JS floating-point edge cases

**File:** `src/cost.ts` line 79

Both implementations are equivalent for practical token counts. The JS version can theoretically introduce rounding drift for very large token counts (>1e12) due to 64-bit float precision. Not a real concern for production workloads.

### L3 — `strTruncate` in `tracer.ts` uses `s.slice(0, limit)` while Python uses `str(v)[:limit]` — both correct

No issue; just confirming parity.

### L4 — `tsup.config.ts` doesn't set `splitting: false` — for a small SDK this is fine

Bundler code-splitting is unnecessary for a single-entry SDK. Current config is acceptable.

### L5 — `index.ts` exports `postSpans` and `postTrace` from transport as part of public API

These are internal implementation details. Exporting them means any consumer can call them directly and bypass the tracer's span stack. Consider removing from public exports or moving to a `transport` sub-export path (`agentlens-observe/transport`).

---

## Edge Cases Found by Scout

1. **Concurrent `trace()` calls that share the singleton `Tracer` but different `AsyncLocalStorage` contexts** — covered by the test `async context isolation`, confirmed correct.

2. **`span().enter()` called twice** — `entered` flag in `SpanContext` prevents double-push, but `span` is already added to `active.spans` via `pushSpan` on first `enter()`. A second `enter()` would push a duplicate onto `spanStack` but NOT onto `spans` array. Exit on second call would pop incorrectly. This is an edge case, low risk since manual span management is explicit.

3. **`trace()` called from within another `trace()`** — `traceStorage.run()` creates a nested `AsyncLocalStorage` context. The inner trace creates a new `ActiveTrace` so spans are isolated. Inner trace posts independently. Outer trace's `postTrace` also runs — two HTTP calls go out. This is correct behavior (nested agents as separate traces), but it's not documented.

4. **`flushBatch()` called after `_resetBatchState()`** — `_batchEnabled` becomes false so `flushBatch` short-circuits correctly. Safe.

5. **`AbortSignal.timeout(5000)` — available in Node 18+** — correct, covered by `engines.node >= 18` in `package.json`.

6. **Empty `spans` array sent to server** — possible if `trace()` completes synchronously with no child spans. The root span is still included so payload always has at least 1 span. Safe.

---

## Positive Observations

- Zero runtime dependencies — native fetch, `node:async_hooks`, `node:crypto` only. Excellent decision.
- `AsyncLocalStorage` usage is textbook correct — `run()` scopes the context, `getStore()` reads it. Concurrent traces are properly isolated (confirmed by test).
- `NoopSpanContext` pattern is clean — callers never need to null-check span results.
- `unref()` on batch timer is excellent — prevents Node process from hanging at exit.
- `_resetBatchState` / `_getBatchQueueLength` test helpers are properly namespaced with `_` prefix to signal internal-only use.
- `SpanExporter` protocol mirrors Python cleanly enough for cross-SDK exporter implementations.
- tsup config producing both ESM + CJS is correct for maximum ecosystem compatibility.
- All 30 tests pass, typecheck clean — solid baseline.

---

## Recommended Actions (Prioritized)

1. **[H2]** Add `input` option to `trace()` signature so root span input can be captured.
2. **[H3]** Reset `_serverUrl` inside `_resetBatchState()` to prevent test pollution.
3. **[M1]** Move `exporters` array into `Tracer` class to eliminate module-level singleton state.
4. **[M2]** Export `ISpanContext` interface so `span()` return type is annotatable.
5. **[M3]** Add `"DOM"` to `tsconfig.json` lib array for proper `fetch`/`Response` type resolution.
6. **[H1]** Add API divergence notes in docstrings for `setCost` signature and `exportSpan` vs `export_span`.
7. **[M5]** Add `repository`, `homepage`, `author` to `package.json`.
8. **[L5]** Consider removing `postSpans` / `postTrace` from public `index.ts` exports.

---

## Metrics

- Type Coverage: ~100% (typecheck passes with `strict: true`)
- Test Coverage: 30 tests across 3 files; all core paths covered (happy path, errors, async isolation, batch, streaming)
- Linting Issues: 0 (no linter configured — consider adding `eslint` with `@typescript-eslint` for future)
- Build: passing (ESM + CJS dual output)

---

## Unresolved Questions

1. Is the TypeScript SDK intended to be published to npm? If yes, when — before or after Python v0.3.0 alignment?
2. Should nested `trace()` calls (trace within a trace) create child spans in the outer trace, or always independent traces? Currently they're independent — is that intentional?
3. Browser support planned? If yes, `node:async_hooks` import will break; would need a polyfill or separate browser entrypoint using `AsyncContext` proposal.
4. Should `streaming` mode emit root span when it completes (currently it does via `flushSpan` in `exit()`), then also post the full trace via `postTrace`? This causes double-send of all spans in streaming mode — is that intentional for server idempotency?
