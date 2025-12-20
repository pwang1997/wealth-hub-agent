import logging
from typing import Sequence

import httpx


class AlphaVantageRestClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"

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

        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ",".join(tickers),
            "limit": limit,
            "apikey": self.api_key,
        }

        response = httpx.get(self.base_url, params=params)
        response.raise_for_status()
        data = response.json()
        logging.debug(f"[get_news_sentiments]: {data}")
        return data
