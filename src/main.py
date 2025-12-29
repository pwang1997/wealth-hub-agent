import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
alpha_vantage_api_key = os.getenv("ALPHAVANTAGE_API_KEY")


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

app = FastAPI(title="Wealth Hub Agent API", logger=logging.getLogger(__name__))


@app.get("/health")
async def health_check():
    return {"status": "ok"}
