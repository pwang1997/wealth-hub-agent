import os
from typing import ClassVar

from dotenv import load_dotenv


class EdgarConfig:
    load_dotenv()
    SEC_TICKER_CIK_URL: ClassVar[str] = "https://www.sec.gov/files/company_tickers.json"
    SEC_SUBMISSIONS_URL: ClassVar[str] = "https://data.sec.gov/submissions/CIK{cik}.json"
    SEC_ARCHIVES_BASE: ClassVar[str] = "https://www.sec.gov/Archives/edgar/data"
    HEADERS: ClassVar[dict] = {
        "User-Agent": f"wealth-hub-agent {os.getenv('CONTACT_EMAIL', 'your-email@email.com')}"
    }
