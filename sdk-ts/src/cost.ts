/**
 * Token cost table — USD per 1M tokens (input, output).
 * Port of Python sdk/agentlens/cost.py. Update periodically from provider pricing.
 * Last updated: 2026-02
 */

/** [inputPricePerMillion, outputPricePerMillion] */
const MODEL_PRICES: ReadonlyMap<string, readonly [number, number]> = new Map([
  // OpenAI — GPT-4o family
  ["gpt-4o", [2.5, 10.0]],
  ["gpt-4o-mini", [0.15, 0.6]],
  // OpenAI — GPT-4.1 family (2025)
  ["gpt-4.1", [2.0, 8.0]],
  ["gpt-4.1-mini", [0.4, 1.6]],
  ["gpt-4.1-nano", [0.1, 0.4]],
  // OpenAI — GPT-4.5
  ["gpt-4.5-preview", [75.0, 150.0]],
  // OpenAI — legacy
  ["gpt-4-turbo", [10.0, 30.0]],
  ["gpt-3.5-turbo", [0.5, 1.5]],
  // OpenAI — reasoning
  ["o1", [15.0, 60.0]],
  ["o1-mini", [3.0, 12.0]],
  ["o3-mini", [1.1, 4.4]],
  ["o3", [10.0, 40.0]],
  // Anthropic — Claude 3.5
  ["claude-3-5-sonnet", [3.0, 15.0]],
  ["claude-3-5-haiku", [0.8, 4.0]],
  ["claude-3-opus", [15.0, 75.0]],
  // Anthropic — Claude 4 (2025)
  ["claude-sonnet-4", [3.0, 15.0]],
  ["claude-haiku-4", [0.8, 4.0]],
  ["claude-opus-4", [15.0, 75.0]],
  // Google — Gemini 1.5
  ["gemini-1.5-pro", [3.5, 10.5]],
  ["gemini-1.5-flash", [0.075, 0.3]],
  // Google — Gemini 2.0 (2025)
  ["gemini-2.0-flash", [0.1, 0.4]],
  ["gemini-2.0-pro", [1.25, 10.0]],
  // DeepSeek
  ["deepseek-v3", [0.27, 1.1]],
  ["deepseek-r1", [0.55, 2.19]],
  // Meta — Llama (via providers)
  ["llama-3.1-70b", [0.52, 0.75]],
  ["llama-3.1-405b", [3.0, 3.0]],
  ["llama-3.3-70b", [0.39, 0.59]],
]);

/**
 * Calculate USD cost for a model call. Returns null if model unknown.
 * Supports fuzzy matching: strips provider prefix (e.g. "openai/gpt-4o" → "gpt-4o"),
 * case-insensitive, and prefix matching.
 */
export function calculateCost(
  model: string,
  inputTokens: number,
  outputTokens: number,
): number | null {
  // Strip provider prefix and lowercase
  const key = model.split("/").pop()!.toLowerCase();

  // Try exact match first
  let prices = MODEL_PRICES.get(key);

  // Fallback: prefix matching in both directions
  if (!prices) {
    for (const [k, v] of MODEL_PRICES) {
      if (key.startsWith(k) || k.startsWith(key)) {
        prices = v;
        break;
      }
    }
  }

  if (!prices) return null;

  const [inPrice, outPrice] = prices;
  const usd = (inputTokens * inPrice + outputTokens * outPrice) / 1_000_000;
  return Math.round(usd * 1_000_000) / 1_000_000; // 6 decimal places
}
