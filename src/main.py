import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Wealth Hub Agent API")

@app.get("/health")
async def health_check():
  return {"status": "ok"}
