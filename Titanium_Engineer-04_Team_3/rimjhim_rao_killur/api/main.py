from fastapi import FastAPI 

from fastapi.middleware.cors import CORSMiddleware 

from pydantic import BaseModel 

from openai import OpenAI 

import os 

from dotenv import load_dotenv 

#Rimjhim

load_dotenv()  # loads .env from parent folder automatically 

  

app = FastAPI() 

app.add_middleware(CORSMiddleware, allow_origins=["*"], 

    allow_methods=["*"], allow_headers=["*"]) 

  

client = OpenAI( 

    api_key=os.getenv("OPENAI_API_KEY"), 

    base_url=os.getenv("OPENAI_BASE_URL") 

) 

  

class ChatRequest(BaseModel): 

    message: str 

  

@app.get("/") 

def health(): 

    return {"status": "Mindful Coach is running","deployed by": "Rimjhim Rao Killur"}

  

@app.post("/chat") 

def chat(req: ChatRequest): 

    response = client.chat.completions.create( 

        model=os.getenv("LLM_MODEL", "gpt-5.5"), 

        messages=[ 

            {"role": "system", "content": "You are a compassionate Mindful Coach. Help users with stress management, mindfulness, and work-life balance. Keep responses warm, supportive, and practical."},

            {"role": "user", "content": req.message} 

        ] 

    ) 

    return {"response": response.choices[0].message.content}