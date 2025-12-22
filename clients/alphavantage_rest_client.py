import logging
from typing import Sequence

import httpx


class AlphaVantageRestClient:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_news_sentiments(self, tickers: Sequence[str], limit: int = 10):
        """
        https://www.alphavantage.co/documentation/#news-sentiment
        Retrieves the news sentiment feed for the requested tickers.

        Args:
            tickers: List of stock symbols that should be included in the request.
            limit: Maximum number of articles to request from Alpha Vantage.
        """

        if not tickers:
            raise ValueError("Tickers list must contain at least one symbol.")
        try:            
            params = {
                "function": "NEWS_SENTIMENT",
                "tickers": ",".join(tickers),
                "limit": limit,
                "apikey": self.api_key,
            }

            response = httpx.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            logging.debug(f"[get_news_sentiments]: {data}")
            return data
        except httpx.HTTPError as e:
            logging.error(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            logging.error(f"Failed to fetch news sentiments from Alpha Vantage: {e}")
            raise RuntimeError(f"Failed to fetch news sentiments from Alpha Vantage: {e}")