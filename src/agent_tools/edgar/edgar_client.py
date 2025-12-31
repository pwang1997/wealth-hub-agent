from __future__ import annotations

import requests

from src.utils.edgar_config import EdgarConfig


def get_cik_for_ticker(ticker: str) -> str:
    resp = requests.get(EdgarConfig.SEC_TICKER_CIK_URL, headers=EdgarConfig.HEADERS, timeout=10)
    resp.raise_for_status()

    data = resp.json()
    ticker_upper = ticker.upper()

    for entry in data.values():
        if entry["ticker"].upper() == ticker_upper:
            return str(entry["cik_str"]).zfill(10)

    raise ValueError(f"CIK not found for ticker: {ticker}")


def build_filing_href(cik: str, accession: str, document: str) -> str:
    accession_no_dashes = accession.replace("-", "")
    return f"{EdgarConfig.SEC_ARCHIVES_BASE}/{int(cik)}/{accession_no_dashes}/{document}"

