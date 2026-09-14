from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
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

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def health():
    return {"status": "AI Project Co-Pilot is running"}

@app.post("/chat")
def chat(req: ChatRequest):
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-5.5"),
        messages=[
            {
                "role": "system",
                "content": (
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
            },
            {"role": "user", "content": req.message}
        ]
    )
    return {"response": response.choices[0].message.content}
