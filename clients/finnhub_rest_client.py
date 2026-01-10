from typing import Literal

import finnhub
import httpx


class FinnHubRestClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.finnhub_client = None

    def init(self):
        self.finnhub_client = finnhub.Client(api_key=self.api_key)

    async def _get(self, path: str, params: dict) -> object:
        url = f"https://finnhub.io/api/v1/{path.lstrip('/')}"
        final_params = {**params, "token": self.api_key}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=final_params)
        response.raise_for_status()
        return response.json()

    def get_company_news(
        self, symbol: str, from_date: str | None = None, to_date: str | None = None
    ):
        """
        https://finnhub.io/docs/api/market-news
        Docstring for get_company_news

        :param self: Description
        :param symbol: Description
        :type symbol: str
        :param from_date: Description
        :type from_date: Optional[str]
        :param to_date: Description
        :type to_date: Optional[str]
        """
        data = self.finnhub_client.company_news(symbol, _from=from_date, to=to_date)
        print(data)
        return data

    async def get_company_news_async(
        self, symbol: str, from_date: str | None = None, to_date: str | None = None
    ):
        """
        https://finnhub.io/docs/api/company-news
        """
        return await self._get(
            "company-news",
            {"symbol": symbol, "from": from_date, "to": to_date},
        )

    def get_company_peer(self, symbol: str, grouping: str | None = None):
        """
        https://finnhub.io/docs/api/company-peers
        Docstring for get_company_peer

        :param self: Description
        :param symbol: Description
        :type symbol: str
        :param grouping: Description
        :type grouping: Optional[str]
        """
        data = self.finnhub_client.company_peers(symbol, grouping=grouping)
        print(data)
        return data

    async def get_company_peer_async(self, symbol: str, grouping: str | None = None):
        """
        https://finnhub.io/docs/api/company-peers
        """
        params = {"symbol": symbol}
        if grouping:
            params["grouping"] = grouping
        return await self._get("stock/peers", params)

    async def get_financial_reports(
        self,
        symbol: str,
        freq: Literal["annual", "quarterly"],
        from_date: str,
        to_date: str,
        access_number: str | None,
    ):
        params = {
            "symbol": symbol,
            "freq": freq,
            "from": from_date,
            "to": to_date,
            "access_number": access_number,
        }
        return await self._get("stock/financials-reported", params)
