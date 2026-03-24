"""
Contextual evidence collector built around direct yfinance news and SEC filing accessors.
Raw Yahoo results are preferred for display; enrichment is optional and must never block display.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Dict, List

import yfinance as yf
from data_collection.yahoo_client import get_info, get_news, get_sec_filings

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "AI Valuation Terminal research contact@localhost.com"}
EXCERPT_KEYWORDS = [
    "revenue",
    "margin",
    "guidance",
    "growth",
    "demand",
    "cash flow",
    "operating income",
    "profit",
    "risk",
    "outlook",
    "services",
    "subscription",
]
FILING_PRIORITY = {
    "10-K": 1,
    "10-Q": 2,
    "8-K": 3,
    "20-F": 4,
    "6-K": 5,
}


def _iso_datetime(value) -> str | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def _split_sentences(text: str) -> List[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text)
    return [_clean_text(chunk) for chunk in chunks if _clean_text(chunk)]


def _score_sentence(sentence: str) -> int:
    lower = sentence.lower()
    score = 0
    for keyword in EXCERPT_KEYWORDS:
        if keyword in lower:
            score += 2
    if any(token in lower for token in ["%", "billion", "million", "$"]):
        score += 1
    if 60 <= len(sentence) <= 320:
        score += 1
    return score


class ContextDataCollector:
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self._info = None

    @property
    def info(self) -> Dict:
        if self._info is None:
            try:
                self._info = get_info(self.stock, self.ticker)
            except Exception as exc:
                logger.warning("[%s] info lookup failed: %s", self.ticker, exc)
                self._info = {}
        return self._info

    def get_business_description(self) -> Dict:
        return {
            "description": self.info.get("longBusinessSummary", "Description not available."),
            "industry_positioning": f"{self.info.get('sector')} / {self.info.get('industry')}",
            "source_url": f"https://finance.yahoo.com/quote/{self.ticker}/profile",
            "timestamp": datetime.now().isoformat(),
        }

    def get_recent_news(self, count: int = 5) -> List[Dict]:
        records: List[Dict] = []
        try:
            raw_items = get_news(self.stock, self.ticker, count=count, tab="news")
        except Exception as exc:
            logger.warning("[%s] get_news failed: %s", self.ticker, exc)
            raw_items = []

        for item in raw_items[:count]:
            content = item.get("content", {}) or {}
            provider = content.get("provider", {}) or {}
            click_url = (content.get("clickThroughUrl") or {}).get("url")
            canonical_url = (content.get("canonicalUrl") or {}).get("url")
            summary = content.get("summary") or content.get("description") or ""
            if not content.get("title"):
                continue
            records.append(
                {
                    "title": content.get("title"),
                    "summary": summary,
                    "published_at": content.get("pubDate"),
                    "publisher": provider.get("displayName") or "Yahoo Finance",
                    "url": click_url or canonical_url,
                }
            )
        return records

    def get_recent_filings(self, count: int = 5) -> List[Dict]:
        records: List[Dict] = []
        try:
            filings = get_sec_filings(self.stock, self.ticker) or []
        except Exception as exc:
            logger.warning("[%s] get_sec_filings failed: %s", self.ticker, exc)
            filings = []

        filings = sorted(
            filings,
            key=lambda filing: (
                FILING_PRIORITY.get((filing.get("type") or "").upper(), 99),
                str(filing.get("date") or ""),
            ),
        )

        for filing in filings[:count]:
            exhibits = filing.get("exhibits", {}) or {}
            filing_type = filing.get("type")
            raw_text = filing.get("title") or filing_type or "Filing record available."
            raw_summary = f"{filing_type or 'Filing'} filed on {_iso_datetime(filing.get('date')) or 'unknown date'}."
            record = {
                "date": _iso_datetime(filing.get("date")),
                "type": filing_type,
                "title": filing.get("title"),
                "edgar_url": filing.get("edgarUrl"),
                "primary_doc_url": exhibits.get(filing_type),
                "excel_url": exhibits.get("EXCEL"),
                "press_release_url": exhibits.get("EX-99.1"),
                "summary": raw_summary,
                "excerpt": raw_text,
            }
            records.append(record)
        return records

    def build_call_excerpts(self, filings: List[Dict]) -> List[Dict]:
        excerpts: List[Dict] = []
        for filing in filings:
            if filing.get("type") not in {"8-K", "10-K", "10-Q"}:
                continue
            excerpt_text = filing.get("excerpt") or filing.get("summary") or filing.get("title") or "Filing record available."
            excerpts.append(
                {
                    "excerpt": excerpt_text,
                    "source": {
                        "provider": filing.get("type") or "SEC filing",
                        "citation": filing.get("press_release_url") or filing.get("primary_doc_url") or filing.get("edgar_url"),
                        "published_at": filing.get("date"),
                    },
                }
            )
        return excerpts[:5]

    def collect_context(self) -> Dict:
        business_description = self.get_business_description()
        recent_news = self.get_recent_news(count=5)
        filing_excerpts = self.get_recent_filings(count=5)
        call_excerpts = self.build_call_excerpts(filing_excerpts)
        return {
            "business_description": business_description,
            "recent_news": recent_news,
            "filing_excerpts": filing_excerpts,
            "call_excerpts": call_excerpts,
            "earnings_guidance_note": "Recent filings and company news should be cross-checked before finalizing narrative assumptions.",
            "data_source": "Yahoo Finance profile, Yahoo Finance news, and Yahoo Finance SEC filings",
        }
