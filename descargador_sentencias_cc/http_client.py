"""Cliente HTTP respetuoso: user-agent identificable, límite de tasa y reintentos con backoff."""

from __future__ import annotations

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config

logger = logging.getLogger(__name__)


class RateLimitedClient:
    """Envoltorio de requests.Session que espacia las solicitudes y reintenta ante fallos transitorios."""

    def __init__(
        self,
        rate_limit_seconds: float = config.RATE_LIMIT_SECONDS,
        timeout: int = config.REQUEST_TIMEOUT_SECONDS,
        max_retries: int = config.MAX_RETRIES,
        user_agent: str = config.USER_AGENT,
    ) -> None:
        self.rate_limit_seconds = rate_limit_seconds
        self.timeout = timeout
        self._last_request_ts: float | None = None

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        retry = Retry(
            total=max_retries,
            backoff_factor=config.BACKOFF_FACTOR,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _throttle(self) -> None:
        if self._last_request_ts is None:
            return
        elapsed = time.monotonic() - self._last_request_ts
        remaining = self.rate_limit_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def get(self, url: str, params: dict | None = None, **kwargs) -> requests.Response:
        self._throttle()
        logger.debug("GET %s params=%s", url, params)
        response = self.session.get(url, params=params, timeout=self.timeout, **kwargs)
        self._last_request_ts = time.monotonic()
        response.raise_for_status()
        return response

    def get_text(self, url: str, params: dict | None = None, **kwargs) -> str:
        response = self.get(url, params=params, **kwargs)
        response.encoding = response.encoding or "utf-8"
        return response.text

    def get_bytes(self, url: str, params: dict | None = None, **kwargs) -> bytes:
        response = self.get(url, params=params, **kwargs)
        return response.content

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "RateLimitedClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
