"""Server-side LLM client for section drafting + chat.

Talks to Azure/APIM (or any OpenAI-compatible endpoint) via the OpenAI SDK.
The API key stays on the server; the frontend never calls the model directly.

Configuration is read from environment variables. Any of these name sets works
(checked in order), so an existing `.env` does not need renaming:
    key   : APIM_API_KEY  | OPENAI_API_KEY | LLM_API_KEY
    base  : APIM_BASE_URL | OPENAI_BASE_URL | LLM_API_BASE
    model : APIM_MODEL    | OPENAI_MODEL    | LLM_MODEL   (default: gpt-5.5)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI

_LLM_ENV_KEYS = {
    "APIM_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY",
    "APIM_BASE_URL", "OPENAI_BASE_URL", "LLM_API_BASE",
    "APIM_MODEL", "OPENAI_MODEL", "LLM_MODEL",
}

_env_loaded = False


def _load_env_files() -> None:
    """Best-effort: pull LLM vars from a `.env` up the tree into os.environ.

    The key often lives in the repo-root `.env`, but the backend runs from
    `backend/`, so those vars are not in the environment. We only set keys that
    are not already present (never override) and only the LLM-related ones.
    """
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True
    for parent in Path(__file__).resolve().parents[:6]:
        candidate = parent / ".env"
        if not candidate.exists():
            continue
        try:
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, _, value = line.partition("=")
                name, value = name.strip(), value.strip().strip('"').strip("'")
                if name in _LLM_ENV_KEYS and name not in os.environ:
                    os.environ[name] = value
        except OSError:
            continue


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def _config() -> tuple[str, str, str]:
    _load_env_files()
    return (
        _first_env("APIM_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY"),
        _first_env("APIM_BASE_URL", "OPENAI_BASE_URL", "LLM_API_BASE"),
        _first_env("APIM_MODEL", "OPENAI_MODEL", "LLM_MODEL", default="gpt-5.5"),
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
