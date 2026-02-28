import { describe, expect, it } from "vitest";
import { calculateCost } from "../src/cost.js";

describe("calculateCost", () => {
  it("calculates cost for known model (gpt-4o)", () => {
    // gpt-4o: $2.50/1M input, $10.00/1M output
    const cost = calculateCost("gpt-4o", 1_000_000, 1_000_000);
    expect(cost).toBe(12.5);
  });

  it("calculates cost for small token counts", () => {
    // gpt-4o: 500 input * 2.50/1M + 200 output * 10.00/1M
    const cost = calculateCost("gpt-4o", 500, 200);
    expect(cost).toBe(0.00325);
  });

  it("returns null for unknown model", () => {
    const cost = calculateCost("unknown-model-xyz", 1000, 1000);
    expect(cost).toBeNull();
  });

  it("strips provider prefix (openai/gpt-4o)", () => {
    const cost = calculateCost("openai/gpt-4o", 1000, 1000);
    expect(cost).not.toBeNull();
    expect(cost).toBeGreaterThan(0);
  });

  it("is case-insensitive", () => {
    const cost = calculateCost("GPT-4O", 1000, 1000);
    expect(cost).not.toBeNull();
  });

  it("supports prefix matching (claude-3-5-sonnet-20240620)", () => {
    // "claude-3-5-sonnet-20240620" starts with "claude-3-5-sonnet"
    const cost = calculateCost("claude-3-5-sonnet-20240620", 1000, 1000);
    expect(cost).not.toBeNull();
    expect(cost).toBeGreaterThan(0);
  });

  it("calculates all 27 models without error", () => {
    const models = [
      "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
      "gpt-4.5-preview", "gpt-4-turbo", "gpt-3.5-turbo",
      "o1", "o1-mini", "o3-mini", "o3",
      "claude-3-5-sonnet", "claude-3-5-haiku", "claude-3-opus",
      "claude-sonnet-4", "claude-haiku-4", "claude-opus-4",
      "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.0-pro",
      "deepseek-v3", "deepseek-r1",
      "llama-3.1-70b", "llama-3.1-405b", "llama-3.3-70b",
    ];
    for (const model of models) {
      const cost = calculateCost(model, 1000, 1000);
      expect(cost, `${model} should have a price`).not.toBeNull();
      expect(cost!, `${model} cost should be positive`).toBeGreaterThan(0);
    }
  });

  it("returns 0 for zero tokens", () => {
    const cost = calculateCost("gpt-4o", 0, 0);
    expect(cost).toBe(0);
  });
});
