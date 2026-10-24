"""LLM client: one function to call a model, behind which the free/paid choice is configuration (S1)."""

from pr_review.llm_client.provider import (
    OPENAI_COMPATIBLE,
    PROVIDERS,
    ProviderUnavailable,
    QuotaExhausted,
    SpikeError,
    call_openai,
    http_attempts,
    pick_provider,
)

LLMError = SpikeError


def complete(provider: str, model: str, prompt: str) -> str:
    """One call, temperature 0. Raises LLMError / QuotaExhausted / ProviderUnavailable."""
    name, key, base = pick_provider(provider)
    if name in OPENAI_COMPATIBLE:
        return call_openai(model, prompt, key, base)
    fn = PROVIDERS[name]
    return fn(model, prompt, key) if name != "gemini" else fn(model, prompt, key, base)


__all__ = ["LLMError", "ProviderUnavailable", "QuotaExhausted", "complete", "http_attempts"]
