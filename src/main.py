import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Wealth Hub Agent API")

openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None

class ChatRequest(BaseModel):
  message: str


class ChatResponse(BaseModel):
  reply: str


@app.get("/health")
async def health_check():
  return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
  if not openai_client:
    raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

  try:
    completion = openai_client.responses.create(
      model="gpt-4.1-mini",
      input=request.message,
    )
    reply = completion.output[0].content[0].text
  except Exception as exc:  # noqa: BLE001
    raise HTTPException(status_code=500, detail=str(exc)) from exc

  return ChatResponse(reply=reply)
