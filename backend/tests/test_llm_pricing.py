"""Tests for the hypothetical cost estimator against curated reference models."""

from app.services.llm_pricing import REFERENCE_MODELS, estimate_cost, rate_per_million_tokens


def test_estimate_cost_returns_a_positive_dollar_amount_for_a_known_model() -> None:
    cost = estimate_cost(prompt_tokens=1_000_000, completion_tokens=1_000_000, reference_key="gpt-4o")

    assert cost is not None
    assert cost > 0


def test_estimate_cost_scales_with_token_count() -> None:
    small = estimate_cost(prompt_tokens=1000, completion_tokens=1000, reference_key="gpt-4o")
    large = estimate_cost(prompt_tokens=1_000_000, completion_tokens=1_000_000, reference_key="gpt-4o")

    assert small is not None
    assert large is not None
    assert large > small


def test_estimate_cost_returns_none_for_an_unmapped_model() -> None:
    cost = estimate_cost(prompt_tokens=1000, completion_tokens=1000, reference_key="not-a-real-model-xyz")

    assert cost is None


def test_every_reference_model_is_actually_priceable() -> None:
    for key in REFERENCE_MODELS.values():
        assert estimate_cost(prompt_tokens=1000, completion_tokens=1000, reference_key=key) is not None, key


def test_rate_per_million_tokens_matches_estimate_cost_at_that_scale() -> None:
    rate = rate_per_million_tokens("gpt-4o")
    cost = estimate_cost(prompt_tokens=1_000_000, completion_tokens=1_000_000, reference_key="gpt-4o")

    assert rate is not None
    input_rate, output_rate = rate
    assert input_rate > 0
    assert output_rate > 0
    assert round(input_rate + output_rate, 6) == round(cost, 6)


def test_rate_per_million_tokens_returns_none_for_an_unmapped_model() -> None:
    assert rate_per_million_tokens("not-a-real-model-xyz") is None
