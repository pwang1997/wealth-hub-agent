
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Sequence, Union

import mcp
from dotenv import load_dotenv
from fastapi.logger import logger
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from clients.alphavantage_rest_client import AlphaVantageRestClient
from src.models.news_sentiments import NewsSentiment

load_dotenv()

class AlphaVantageNewsTool:
    def __init__(self):
        alpha_vantage_api_key = os.getenv("ALPHAVANTAGE_API_KEY")
        if not alpha_vantage_api_key:
            raise ValueError(
                "Alpha Vantage API key not provided! Please set ALPHAVANTAGE_API_KEY environment variable."
            )
        self.client = AlphaVantageRestClient(alpha_vantage_api_key)

    def _normalize_symbols(
        self, symbols: Optional[Union[str, Sequence[str]]]
    ) -> list[str]:
        normalized: list[str] = []
        if isinstance(symbols, str):
            normalized = [part.strip().upper() for part in symbols.split(",") if part.strip()]
        elif isinstance(symbols, Sequence):
            for symbol in symbols:
                if isinstance(symbol, str):
                    cleaned = symbol.strip().upper()
                    if cleaned:
                        normalized.append(cleaned)

        return normalized

    def _parse_iso_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _parse_filter_time(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y%m%dT%H%M")
        except ValueError:
            logger.debug(f"Unable to parse filter time: {value}")
            return None

    def _article_matches_topics(self, article, whitelist: list[str]) -> bool:
        topic_entries = article.get("topics", [])
        for entry in topic_entries:
            candidate = entry.get("topic", "")
            if any(requested in candidate.lower() for requested in whitelist):
                return True
        return False

    def _within_time_window(
        self,
        published_at: Optional[datetime],
        time_from: Optional[datetime],
        time_to: Optional[datetime],
    ) -> bool:
        if not published_at:
            return True
        if (time_from and published_at < time_from) or (time_to and published_at > time_to):
            return False
        return True

    def _fetch_news(
        self,
        symbols: Optional[Union[str, Sequence[str]]] = None,
        topics: Optional[str] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
        sort: str = "LATEST",
        limit: int = 10,
    ) -> list[dict]:
        tickers = self._normalize_symbols(symbols)
        if not tickers:
            raise ValueError("At least one symbol must be provided to fetch Alpha Vantage news.")

        time_from_dt = self._parse_filter_time(time_from)
        time_to_dt = self._parse_filter_time(time_to)
        topic_filters = (
            [topic.strip().lower() for topic in topics.split(",") if topic.strip()]
            if topics
            else []
        )

        try:
            data = self.client.get_news_sentiments(tickers, limit=limit)
            feed = data.get("feed", [])
        except Exception as exc:
            logger.error(f"Alpha Vantage API error: {exc}")
            raise RuntimeError(f"Alpha Vantage API error: {exc}") from exc

        filtered_feed = []
        for article in feed:
            published_at = self._parse_iso_datetime(article.get("time_published"))
            if not self._within_time_window(published_at, time_from_dt, time_to_dt):
                continue
            if topic_filters and not self._article_matches_topics(article, topic_filters):
                continue
            filtered_feed.append(article)

        if sort.upper() == "LATEST":
            filtered_feed.sort(
                key=lambda art: self._parse_iso_datetime(art.get("time_published")) or datetime.min,
                reverse=True,
            )
        elif sort.upper() == "OLDEST":
            filtered_feed.sort(
                key=lambda art: self._parse_iso_datetime(art.get("time_published")) or datetime.max
            )

        return filtered_feed[:max(1, limit)]

    def fetch_news(
        self, symbols: Optional[Union[str, Sequence[str]]] = None, limit: int = 10
    ):
        tickers = self._normalize_symbols(symbols)
        try:
            feed = self._fetch_news(symbols=tickers, limit=limit)
            if not feed:
                logger.warning("⚠️ Alpha Vantage API returned empty feed")
                return []

            ticker_label = ", ".join(tickers) if tickers else "symbol(s)"
            logger.info(f"✅ Fetched {len(feed)} news articles about {ticker_label} from Alpha Vantage")
            return feed
        except ValueError as exc:
            logger.error(exc)
            raise

    def __call__(
        self,
        symbols: Optional[Union[str, Sequence[str]]] = None,
        topics: Optional[str] = None,
        limit: int = 10,
    ):
        """
        Fetches news articles from Alpha Vantage based on symbols and topics.
        Args:
            symbols (str | Sequence[str]): Stock symbols to filter news articles.
            topics (str): Comma-separated topics to filter news articles.
        """
        logger.debug(f"Searching Alpha Vantage news: symbols={symbols}, topics={topics}")
        today_datetime = datetime.now()
        today_date = today_datetime.strftime("%Y-%m-%d %H:%M:%S")
        time_to = today_datetime.strftime("%Y%m%dT%H%M")
        time_from_datetime = today_datetime - timedelta(days=30)
        time_from = time_from_datetime.strftime("%Y%m%dT%H%M")

        logger.debug(
            f"Filtering articles published before: {today_date} "
            f"(API format: time_from={time_from}, time_to={time_to})"
        )

        all_articles = self._fetch_news(
            symbols=symbols,
            topics=topics,
            time_from=time_from,
            time_to=time_to,
            sort="LATEST",
            limit=limit,
        )
        logger.debug(f"Found {len(all_articles)} articles after API filtering")
        return all_articles

alpha_vantage_tool = AlphaVantageNewsTool()

mcp = FastMCP("NewsSearch")

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins; use specific origins for security
        allow_methods=["*"],
        allow_headers=[
            "mcp-protocol-version",
            "mcp-session-id",
            "Authorization",
            "Content-Type",
        ],
        expose_headers=["mcp-session-id"],
    )
]
app = mcp.http_app(middleware=middleware)

@mcp.tool
def get_market_news(symbols: Optional[str] = None, limit: int = 10)->list[NewsSentiment]:
    """Fetches the latest market news articles from Alpha Vantage.

    Args:
        symbols (str): A comma-separated string of stock symbols to filter news articles.
        limit (int): The maximum number of news articles to return.
    Returns:
        A list of news articles related to the specified stock symbols.
    """

    if not symbols:
        logger.warning("⚠️ Please provide at least one comma-separated symbol.")
        return []

    normalized_symbols = [
        ticker.strip().upper() for ticker in symbols.split(",") if ticker.strip()
    ]
    if not normalized_symbols:
        logger.warning("⚠️ Symbol list must contain at least one valid ticker.")
        return []

    try:
        results = alpha_vantage_tool.fetch_news(symbols=normalized_symbols, limit=limit)
        if not results:
            logger.warning(f"⚠️ No news articles found for symbols: {', '.join(normalized_symbols)}")
            return []

        formatted_results = []
        for article in results:
            title = article.get("title", "N/A")
            url = article.get("url", "N/A")
            summary = article.get("summary", "N/A")
            time_published = article.get("time_published", "N/A")
            source = article.get("source", "N/A")

            overall_sentiment = article.get("overall_sentiment_score", "N/A")
            sentiment_label = article.get("overall_sentiment_label", "N/A")
          
            ticker_parts = []
            ticker_sentiment = article.get("ticker_sentiment", [])

            if ticker_sentiment:
                for ticker_info in ticker_sentiment:
                    ticker = ticker_info.get("ticker", "N/A")
                    relevance = ticker_info.get("relevance_score", "N/A")
                    sentiment_score = ticker_info.get("ticker_sentiment_score", "N/A")
                    sentiment_label_ticker = ticker_info.get("ticker_sentiment_label", "N/A")
                    ticker_parts.append(
                        f"{ticker}: relevance={relevance}, sentiment={sentiment_score} ({sentiment_label_ticker})"
                    )

            topics_str = "N/A"
            topics_list = article.get("topics", [])
            if topics_list:
                topics_str = ", ".join([topic.get("topic", "") for topic in topics_list])

            formatted_result = NewsSentiment(title=title,
                          source=source,
                          url=url,
                          summary=summary,
                          topics=topics_str,
                          overall_sentiment=overall_sentiment,
                          sentiment_label=sentiment_label,
                          ticker_sentiment=ticker_parts,
                          time_published=time_published)
            
            formatted_results.append(formatted_result)

        if not formatted_results:
            joined_symbols = ", ".join(normalized_symbols)
            logger.warning(f"⚠️ No news articles found matching criteria '{joined_symbols}' after date filtering.")
            return []

        return formatted_results

    except Exception as e:
        logger.error(f"Error in get_market_news tool: {e}")
        raise RuntimeError(f"Error in get_market_news tool: {e}")
        
        
if __name__ == "__main__":
    # Run with streamable-http, support configuring host and port through environment variables to avoid conflicts
    logger.info("Running Alpha Vantage News Tool as search tool")
    port = int(os.getenv("SEARCH_HTTP_PORT", "8001"))
    mcp.run(transport="streamable-http", port=port)
