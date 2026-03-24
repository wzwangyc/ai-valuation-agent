"""Shared HTTP client with timeout, retry, and backoff controls for data-source access."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class HttpClient:
    """Thin requests wrapper for deterministic retry and logging behavior."""

    def __init__(
        self,
        base_headers: Optional[Dict[str, str]] = None,
        default_timeout: float = 5.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
    ) -> None:
        self.base_headers = base_headers or {}
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.session = requests.Session()

    def get_json(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """GET JSON with bounded retries and explicit logging."""
        merged_headers = {**self.base_headers, **(headers or {})}
        effective_timeout = timeout if timeout is not None else self.default_timeout
        attempts = retries if retries is not None else self.max_retries

        last_error: Exception | None = None
        for attempt in range(attempts + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=merged_headers,
                    timeout=effective_timeout,
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= attempts:
                    logger.warning("HTTP GET failed after %s attempts: %s params=%s error=%s", attempt + 1, url, params, exc)
                    raise
                sleep_for = self.backoff_seconds * (2 ** attempt)
                logger.info(
                    "HTTP GET retry %s/%s for %s params=%s after error=%s",
                    attempt + 1,
                    attempts,
                    url,
                    params,
                    exc,
                )
                time.sleep(sleep_for)

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Unexpected HTTP client failure for {url}")
