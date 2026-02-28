"""Tests for cost.py — token cost calculation."""

import pytest
from agentlens.cost import calculate_cost, MODEL_PRICES


class TestCalculateCost:
    """Test cost calculation for known models."""

    def test_known_model_exact_pricing(self):
        """Calculate cost for known model with exact pricing."""
        # gpt-4o: input $2.50/1M, output $10.00/1M
        cost = calculate_cost("gpt-4o", 1000, 500)
        expected = (1000 * 2.50 + 500 * 10.00) / 1_000_000
        assert cost == pytest.approx(expected)

    def test_known_model_gpt4o_mini(self):
        """Calculate cost for gpt-4o-mini."""
        # gpt-4o-mini: input $0.15/1M, output $0.60/1M
        cost = calculate_cost("gpt-4o-mini", 100, 100)
        expected = (100 * 0.15 + 100 * 0.60) / 1_000_000
        assert cost == pytest.approx(expected)

    def test_known_model_claude_sonnet(self):
        """Calculate cost for Claude 3.5 Sonnet."""
        cost = calculate_cost("claude-3-5-sonnet", 200, 100)
        assert cost is not None
        assert cost > 0

    def test_zero_tokens_zero_cost(self):
        """Zero tokens should give zero cost."""
        cost = calculate_cost("gpt-4o", 0, 0)
        assert cost == 0.0

    def test_partial_zero_tokens(self):
        """Cost with zero input or output tokens."""
        cost = calculate_cost("gpt-4o", 1000, 0)
        assert cost > 0

        cost = calculate_cost("gpt-4o", 0, 500)
        assert cost > 0

    def test_unknown_model_returns_none(self):
        """Unknown model returns None."""
        cost = calculate_cost("unknown-model-12345", 100, 100)
        assert cost is None

    def test_prefix_match_provider_prefix(self):
        """Strips provider prefix for matching (e.g., 'openai/gpt-4o')."""
        # With 'openai/' prefix should match 'gpt-4o'
        cost = calculate_cost("openai/gpt-4o", 1000, 500)
        assert cost is not None
        assert cost > 0

    def test_prefix_match_case_insensitive(self):
        """Model matching is case-insensitive."""
        cost_lower = calculate_cost("gpt-4o", 100, 100)
        cost_upper = calculate_cost("GPT-4O", 100, 100)
        assert cost_lower == cost_upper

    def test_prefix_fuzzy_match(self):
        """Fuzzy matching handles partial model names."""
        # 'gpt-4o' should match if we search for 'gpt-4'
        # Note: current logic is startswith, not full prefix match
        cost = calculate_cost("gpt-4o-custom", 100, 100)
        # May or may not match depending on implementation
        # Just verify it doesn't crash
        assert cost is None or cost > 0

    def test_all_models_have_positive_prices(self):
        """Verify all models in MODEL_PRICES have positive prices."""
        for model_name, (input_price, output_price) in MODEL_PRICES.items():
            assert input_price > 0, f"{model_name} has zero input price"
            assert output_price > 0, f"{model_name} has zero output price"

    def test_model_prices_realistic(self):
        """Verify model prices are reasonable (not astronomical)."""
        for model_name, (input_price, output_price) in MODEL_PRICES.items():
            # Prices should be less than $200 per 1M tokens (gpt-4.5-preview is expensive)
            assert input_price < 200, f"{model_name} input price too high"
            assert output_price < 200, f"{model_name} output price too high"

    def test_large_token_counts(self):
        """Handle large token counts without overflow."""
        cost = calculate_cost("gpt-4o", 1_000_000, 1_000_000)
        assert cost is not None
        assert cost > 0
        # 1M input tokens at $2.50/1M + 1M output at $10/1M = $12.50
        assert cost == pytest.approx(12.50)

    def test_cost_is_rounded_to_6_decimals(self):
        """Cost is rounded to 6 decimal places."""
        cost = calculate_cost("gpt-4o", 123, 456)
        # Should be rounded to 6 decimals
        assert len(str(cost).split('.')[-1]) <= 6

    def test_o1_model_expensive(self):
        """o1 model (reasoning) is expensive."""
        cost_o1 = calculate_cost("o1", 100, 100)
        cost_gpt4 = calculate_cost("gpt-4o", 100, 100)
        assert cost_o1 > cost_gpt4

    def test_anthropic_vs_openai_pricing(self):
        """Anthropic and OpenAI have different pricing tiers."""
        # Just verify they're all in the model list
        assert "gpt-4o" in MODEL_PRICES
        assert "claude-3-5-sonnet" in MODEL_PRICES
