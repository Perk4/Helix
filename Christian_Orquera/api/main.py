from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def health():
    return {"status": "Crypto Analyst is running"}

@app.post("/chat")
def chat(req: ChatRequest):
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-5.5"),
        messages=[
            {"role": "system", "content": "You are an expert Cryptocurrency Analyst. Help users understand blockchain technology, crypto markets, investment strategies, and crypto fundamentals."},
            {"role": "user", "content": req.message}
        ]
    )
    return {"response": response.choices[0].message.content}
