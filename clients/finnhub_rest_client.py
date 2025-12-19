

from typing import Optional

import finnhub


class FinnHubRestClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.finnhub_client = None
        
    def init(self):
        self.finnhub_client = finnhub.Client(api_key=self.api_key)
        
    def get_company_news(self, symbol: str, from_date: Optional[str] = None, to_date: Optional[str] = None):
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
        data = self.finnhub_client.company_news(symbol, _from= from_date, to= to_date)
        print(data)
        
    def get_company_peer(self, symbol: str, grouping: Optional[str] = None):
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