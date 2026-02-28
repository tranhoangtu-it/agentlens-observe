"""Token cost table. Update periodically from provider pricing pages."""
from typing import Optional

# USD per 1M tokens — (input_price, output_price)
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o":            (2.50,  10.00),
    "gpt-4o-mini":       (0.15,   0.60),
    "gpt-4-turbo":       (10.00, 30.00),
    "gpt-3.5-turbo":     (0.50,   1.50),
    "claude-3-5-sonnet": (3.00,  15.00),
    "claude-3-5-haiku":  (0.80,   4.00),
    "claude-3-opus":     (15.00, 75.00),
    "gemini-1.5-pro":    (3.50,  10.50),
    "gemini-1.5-flash":  (0.075,  0.30),
    "o1":                (15.00, 60.00),
    "o1-mini":           (3.00,  12.00),
    "o3-mini":           (1.10,   4.40),
}


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Optional[float]:
    """Return USD cost for a model call. Returns None if model unknown."""
    # Fuzzy match: strip provider prefix (e.g. "openai/gpt-4o" -> "gpt-4o")
    key = model.split("/")[-1].lower()
    # Try exact, then prefix match
    prices = MODEL_PRICES.get(key)
    if not prices:
        for k, v in MODEL_PRICES.items():
            if key.startswith(k) or k.startswith(key):
                prices = v
                break
    if not prices:
        return None
    in_price, out_price = prices
    usd = (input_tokens * in_price + output_tokens * out_price) / 1_000_000
    return round(usd, 6)
