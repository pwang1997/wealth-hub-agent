import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()
alpha_vantage_api_key = os.getenv("ALPHAVANTAGE_API_KEY")


logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

app = FastAPI(title="Wealth Hub Agent API",
              logger=logging.getLogger(__name__))

@app.get("/health")
async def health_check():
  return {"status": "ok"}


@app.get("/news-sentiments")
async def get_news_sentiments(tickers: str, limit: int = 10):
    from clients.alphavantage_rest_client import AlphaVantageRestClient

    if not alpha_vantage_api_key:
        raise HTTPException(status_code=500, detail="AlphaVantage API key not configured")  
    client = AlphaVantageRestClient(alpha_vantage_api_key)
    data = client.get_news_sentiments(tickers.split(","), limit)
    return data
    
