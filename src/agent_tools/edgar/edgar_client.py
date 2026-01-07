from __future__ import annotations

import re

import aiohttp
import requests
from llama_index.core.schema import BaseNode

from src.utils.edgar_config import EdgarConfig


class EdgarClient:
    async def get_cik_for_ticker(ticker: str) -> str:
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

    async def get_filing_content(
        href: str,
        session: aiohttp.ClientSession,
    ) -> str:
        timeout = aiohttp.ClientTimeout(
            total=30,
            connect=10,
            sock_read=20,
        )

        async with session.get(href, timeout=timeout) as resp:
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                raise ValueError(f"Unexpected content type: {content_type}")

            return await resp.text()

    def _normalize_html_nodes(raw_nodes: list[BaseNode]):
        """
        Normalize + filter junk before chunking

        :param raw_nodes: Description
        :type raw_nodes: list[BaseNode]
        """
        cleaned_nodes = []
        item_re = re.compile(r"ITEM\s+\d+[A-Z]?\.", re.IGNORECASE)
        current_section = None

        for n in raw_nodes:
            text = re.sub(r"\s+", " ", n.text or "").strip()
            MIN_TEXT_LEN, MAX_TEXT_LEN = 80, 5000
            if len(text) < MIN_TEXT_LEN or len(text) > MAX_TEXT_LEN:
                continue

            if item_re.search(text):
                current_section = text

            n.text = text
            if current_section:
                n.metadata["section"] = current_section

            cleaned_nodes.append(n)
        return cleaned_nodes
