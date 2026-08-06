"""Hypothetical dollar cost of logged token usage, under a curated set of real paid models.

litellm already fetches live pricing (model_prices_and_context_window.json,
refreshed from its GitHub repo at import time - see litellm/__init__.py's
get_model_cost_map(), with an automatic fallback to a bundled backup on
failure). This module doesn't maintain its own price table: it's just a
curated allowlist of which model keys to price against, on top of litellm's
already-live litellm.cost_per_token(). Each key below was verified live in
this environment to have real, non-zero pricing.

Reference models will need occasional manual upkeep as generations roll over
(swap in the new "latest", drop the retired one) - cheap, since it's only
ever picking which key to point at, never tracking a price by hand.
"""

import litellm

# Display name -> litellm model-cost key. Anthropic + OpenAI only, matching
# model_selection.py's DEFAULT_HOSTED_MODELS provider coverage.
REFERENCE_MODELS: dict[str, str] = {
    "Claude Opus": "claude-opus-4-5-20251101",
    "Claude Sonnet": "claude-sonnet-4-5-20250929",
    "Claude Haiku": "claude-haiku-4-5-20251001",
    "GPT-5": "gpt-5",
    "GPT-5 mini": "gpt-5-mini",
    "GPT-4o": "gpt-4o",
    "GPT-4o mini": "gpt-4o-mini",
}


def rate_per_million_tokens(reference_key: str) -> tuple[float, float] | None:
    """Return a reference model's ($/1M input tokens, $/1M output tokens) rate.

    Args:
        reference_key: A litellm model-cost key, typically one of
            REFERENCE_MODELS's values.

    Returns:
        The (input, output) rate pair in USD per million tokens, or None if
        litellm can't price this model.
    """
    try:
        input_cost, _ = litellm.cost_per_token(model=reference_key, prompt_tokens=1_000_000, completion_tokens=0)
        _, output_cost = litellm.cost_per_token(model=reference_key, prompt_tokens=0, completion_tokens=1_000_000)
    except Exception:
        return None
    return input_cost, output_cost


def estimate_cost(prompt_tokens: int, completion_tokens: int, reference_key: str) -> float | None:
    """Estimate the dollar cost of a token count under a reference model's real pricing.

    Args:
        prompt_tokens: Number of prompt/input tokens.
        completion_tokens: Number of completion/output tokens.
        reference_key: A litellm model-cost key, typically one of
            REFERENCE_MODELS's values.

    Returns:
        The estimated cost in USD, or None if litellm can't price this
        model (kept distinct from 0.0, which means "genuinely free").
    """
    try:
        input_cost, output_cost = litellm.cost_per_token(
            model=reference_key, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )
    except Exception:
        return None
    return input_cost + output_cost
