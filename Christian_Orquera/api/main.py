from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI
import json
import os
import traceback
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = (os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
MODEL = os.getenv("LLM_MODEL", "gpt-5.5")

SYSTEM_PROMPT = (
    "You are an expert Cryptocurrency Analyst. Help users understand blockchain "
    "technology, crypto markets, investment strategies, and crypto fundamentals."
)

# Exercise 2's APIM gateway exposes only the Responses API and takes the key as
# a query param. Exercise 1's direct Azure OpenAI endpoint uses chat/completions
# with a normal auth header. Pick the shape from whichever URL is configured.
USE_APIM = "azure-api.net" in BASE_URL

if USE_APIM:
    if BASE_URL.endswith("/responses"):
        BASE_URL = BASE_URL[: -len("/responses")]
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        default_query={"subscription-key": API_KEY},
    )
else:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

TICKER_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# Binance blocks datacenter IP ranges, so both of its hosts 451 from App
# Service even though they work from a desktop. CoinGecko is the fallback.
BINANCE_HOSTS = ["https://api.binance.us", "https://api.binance.com"]

COINGECKO_IDS = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
}


async def _from_binance(http):
    params = {"symbols": json.dumps(TICKER_SYMBOLS)}
    for host in BINANCE_HOSTS:
        try:
            res = await http.get(f"{host}/api/v3/ticker/24hr", params=params)
        except httpx.HTTPError:
            continue
        if res.status_code != 200:
            continue
        return [
            {
                "symbol": t["symbol"],
                "lastPrice": t["lastPrice"],
                "priceChangePercent": t["priceChangePercent"],
            }
            for t in res.json()
        ]
    return None


async def _from_coingecko(http):
    params = {
        "ids": ",".join(COINGECKO_IDS),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }
    try:
        res = await http.get("https://api.coingecko.com/api/v3/simple/price", params=params)
    except httpx.HTTPError:
        return None
    if res.status_code != 200:
        return None

    data = res.json()
    tickers = []
    for gecko_id, symbol in COINGECKO_IDS.items():
        entry = data.get(gecko_id)
        if not entry:
            continue
        tickers.append(
            {
                "symbol": symbol,
                "lastPrice": str(entry["usd"]),
                "priceChangePercent": str(round(entry.get("usd_24h_change", 0.0), 2)),
            }
        )
    return tickers or None

def _response_text(response):
    """Pull assistant text out of a Responses payload.

    Reasoning models emit a `reasoning` item alongside the `message`, which
    some SDK versions mishandle in `output_text`, so fall back to walking the
    output items directly.
    """
    try:
        text = response.output_text
        if text:
            return text
    except Exception:
        pass

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
    return {"status": "Crypto Analyst is running"}

@app.get("/debug")
def debug():
    import openai
    return {
        "openai": openai.__version__,
        "httpx": httpx.__version__,
        "use_apim": USE_APIM,
        "model": MODEL,
        "base_url_host": BASE_URL.split("/")[2] if "//" in BASE_URL else None,
    }

@app.get("/ticker")
async def ticker():
    async with httpx.AsyncClient(timeout=10) as http:
        for source in (_from_binance, _from_coingecko):
            tickers = await source(http)
            if tickers:
                return {"tickers": tickers}

    return JSONResponse({"error": "Unable to reach price feed"}, status_code=502)

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        if USE_APIM:
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
