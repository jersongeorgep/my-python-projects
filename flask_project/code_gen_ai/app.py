#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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str

USE_MOCK = True  # toggle this for testing


@app.post("/generate")
async def generate_code(req: PromptRequest):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": f"Write code for: {req.prompt}"}
        ],
        temperature=0.2
    )

    return {"code": response.choices[0].message.content}