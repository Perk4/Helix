"""Server-side LLM client for section drafting + chat.

Talks to Azure/APIM (or any OpenAI-compatible endpoint) via the OpenAI SDK.
The API key stays on the server; the frontend never calls the model directly.

Configuration is read from environment variables (matching draft_pipeline.py):
    APIM_API_KEY   — gateway / API key
    APIM_BASE_URL  — e.g. https://<org>.azure-api.net/gpt51/openai
    APIM_MODEL     — deployment / model name (default: gpt-5.5)
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI


def _config() -> tuple[str, str, str]:
    return (
        os.environ.get("APIM_API_KEY", ""),
        os.environ.get("APIM_BASE_URL", ""),
        os.environ.get("APIM_MODEL", "gpt-5.5"),
    )


def is_configured() -> bool:
    """True when an API key is present, so callers can degrade gracefully."""
    return bool(_config()[0])


@lru_cache
def _client() -> OpenAI:
    from openai import OpenAI  # lazy: the app imports without the SDK installed

    key, base, model = _config()
    if base and "azure-api.net" in base:
        # APIM: deployment in the path, auth via subscription-key query param.
        return OpenAI(
            api_key=key,
            base_url=f"{base.rstrip('/')}/deployments/{model}",
            default_query={"subscription-key": key},
        )
    if base:
        return OpenAI(api_key=key, base_url=base)
    return OpenAI(api_key=key)


def chat(
    messages: list[dict],
    *,
    temperature: float = 0.0,
    max_tokens: int = 2000,
    seed: int | None = 7,
) -> str:
    """Return the assistant text for a chat-completions request.

    Uses temperature 0 (+ a fixed seed) for consistent, low-drift output. Some
    Azure deployments reject those knobs; if so, we retry without them.
    """
    if not is_configured():
        raise RuntimeError("APIM_API_KEY is not set; the model is unavailable.")
    _, _, model = _config()
    base = {"model": model, "messages": messages, "max_completion_tokens": max_tokens}
    try:
        response = _client().chat.completions.create(temperature=temperature, seed=seed, **base)
    except Exception:
        response = _client().chat.completions.create(**base)
    return (response.choices[0].message.content or "").strip()
