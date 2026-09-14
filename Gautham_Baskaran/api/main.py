from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import httpx
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env from parent folder automatically

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

SYSTEM_PROMPT = (
    "You are an AI Project Co-Pilot — a senior AI strategy advisor helping "
    "organizations decide whether and how to build AI solutions. "
    "When a user describes an AI project idea or business problem, respond with a structured analysis using EXACTLY this format:\n\n"
    "🎯 RECOMMENDED APPROACH\n"
    "[Choose one: RAG / Agentic / Fine-tuning / Prompt Engineering / Hybrid] — explain why in 2 sentences.\n\n"
    "📊 FEASIBILITY SCORE: X/10\n"
    "Technical: X/10 | Organizational: X/10\n"
    "[Brief reasoning in 2 sentences]\n\n"
    "⚠️ TOP 3 RISKS\n"
    "1. [Risk name]: [What goes wrong] → Mitigation: [How to prevent it]\n"
    "2. [Risk name]: [What goes wrong] → Mitigation: [How to prevent it]\n"
    "3. [Risk name]: [What goes wrong] → Mitigation: [How to prevent it]\n\n"
    "💼 EXECUTIVE PITCH\n"
    "[One compelling paragraph a non-technical executive would immediately understand. "
    "Include the business value, timeframe, and a measurable outcome.]\n\n"
    "⚡ QUICK WIN (2-Week Prototype)\n"
    "[Concrete, specific thing to build and demo in 2 weeks that proves the concept with minimal risk.]\n\n"
    "Keep responses sharp, opinionated, and actionable. You are not a chatbot — you are a trusted AI strategy partner."
)


def _is_apim(base_url: str) -> bool:
    """Detect APIM gateway — it uses Responses API, not Chat Completions."""
    return "azure-api.net" in (base_url or "")


def _chat_via_apim(api_key: str, base_url: str, model: str, user_message: str) -> str:
    """Call APIM Responses API. Auth via subscription-key query param."""
    url = base_url.rstrip("/") + "/responses"
    payload = {
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": user_message,
    }
    with httpx.Client(timeout=60) as http:
        resp = http.post(url, params={"subscription-key": api_key}, json=payload)
        resp.raise_for_status()
        data = resp.json()

    # Extract assistant text from output array (skip reasoning blocks)
    for item in data.get("output", []):
        if item.get("type") == "message" and item.get("content"):
            return item["content"][0]["text"]

    raise HTTPException(status_code=502, detail="No message output in APIM response")


def _chat_via_openai(api_key: str, base_url: str, model: str, user_message: str) -> str:
    """Call Azure OpenAI directly via Chat Completions API."""
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
    )
    return response.choices[0].message.content


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def health():
    return {"status": "AI Project Co-Pilot is running"}


@app.post("/chat")
def chat(req: ChatRequest):
    api_key  = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model    = os.getenv("LLM_MODEL", "gpt-5.5")

    if _is_apim(base_url):
        text = _chat_via_apim(api_key, base_url, model, req.message)
    else:
        text = _chat_via_openai(api_key, base_url, model, req.message)

    return {"response": text}
