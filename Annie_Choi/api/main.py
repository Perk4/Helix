"""Mindful Coach — Titanium IDE Challenge backend (Annie Choi).

A minimal FastAPI service with one health route and one /chat route that calls
the Accenture-provided GPT-5.5 model through the individual APIM gateway.

Keys are read from a .env at the team repo root (load_dotenv walks up to find
it). Per the IDE Challenge Guide and the labs .env, the individual APIM key is
placed in OPENAI_API_KEY and the gateway in OPENAI_BASE_URL:

    OPENAI_API_KEY=<your-individual-apim-key>   # or ${APIM_KEY}
    OPENAI_BASE_URL=https://lgts1tetamapi01.azure-api.net/gpt51/openai
    LLM_MODEL=gpt-5.5
"""

import os
import traceback

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()  # finds the .env at the team repo root automatically

app = FastAPI(title="Mindful Coach")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL = os.getenv("LLM_MODEL", "gpt-5.5")

SYSTEM_PROMPT = (
    "You are a compassionate Mindful Coach. Help the user manage stress, build "
    "healthy habits, and practice mindfulness. Offer warm, practical, concrete "
    "suggestions in a few sentences. You are not a medical professional; gently "
    "encourage the user to seek qualified help for any serious concern."
)


def _client() -> OpenAI:
    """Build the OpenAI client against the configured endpoint.

    The bootcamp default points OPENAI_BASE_URL at the Accenture APIM gateway.
    APIM authenticates on the subscription key sent as the Ocp-Apim-Subscription-Key
    header (and subscription-key query param), NOT the OpenAI SDK's default
    Authorization: Bearer header, so we attach both when talking to the gateway.
    A Direct OpenAI key still works if one is dropped in later (leave
    OPENAI_BASE_URL blank for that fallback — no APIM headers are added).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = (os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
    kwargs = {"api_key": api_key, "base_url": base_url or None}
    if "azure-api.net" in base_url:
        kwargs["default_headers"] = {"Ocp-Apim-Subscription-Key": api_key}
        kwargs["default_query"] = {"subscription-key": api_key}
    return OpenAI(**kwargs)


def _is_apim() -> bool:
    return "azure-api.net" in (os.getenv("OPENAI_BASE_URL") or "")


def _response_text(response) -> str:
    """Pull assistant text out of a Responses payload.

    Reasoning models emit a `reasoning` item alongside the `message`, which some
    SDK versions leave out of `output_text`, so fall back to walking the items.
    """
    text = getattr(response, "output_text", None)
    if text:
        return text
    parts = []
    for item in getattr(response, "output", None) or []:
        for chunk in getattr(item, "content", None) or []:
            chunk_text = getattr(chunk, "text", None)
            if chunk_text:
                parts.append(chunk_text)
    return "".join(parts)


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def health():
    return {"status": "Mindful Coach is running", "deployed_by": "Annie Choi"}


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        client = _client()
        # The APIM gateway exposes the Responses API (/responses), not
        # chat/completions. A Direct OpenAI endpoint uses chat/completions.
        if _is_apim():
            response = client.responses.create(
                model=MODEL,
                instructions=SYSTEM_PROMPT,
                input=req.message,
            )
            return {"response": _response_text(response)}

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": req.message},
            ],
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            {"error": f"{type(e).__name__}: {e}"[:400]}, status_code=502
        )
