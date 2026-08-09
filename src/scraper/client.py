"""Cliente HTTP respetuoso: user-agent identificable, límite de tasa y reintentos con backoff."""

from __future__ import annotations

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src import config

logger = logging.getLogger(__name__)


class RateLimitedClient:
    """Envoltorio sobre requests.Session que aplica una pausa mínima entre solicitudes
    y reintenta automáticamente errores transitorios (5xx, timeouts, conexión)."""

    def __init__(
        self,
        rate_limit_seconds: float = config.DEFAULT_RATE_LIMIT_SECONDS,
        timeout_seconds: float = config.DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = config.DEFAULT_MAX_RETRIES,
        backoff_base_seconds: float = config.DEFAULT_BACKOFF_BASE_SECONDS,
        user_agent: str = config.USER_AGENT,
    ) -> None:
        self.rate_limit_seconds = rate_limit_seconds
        self.timeout_seconds = timeout_seconds
        self._last_request_ts: float | None = None

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Language": "es-CO,es;q=0.9",
            }
        )

        retry = Retry(
            total=max_retries,
            backoff_factor=backoff_base_seconds,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _throttle(self) -> None:
        if self._last_request_ts is None:
            return
        elapsed = time.monotonic() - self._last_request_ts
        wait = self.rate_limit_seconds - elapsed
        if wait > 0:
            time.sleep(wait)

    def get(self, url: str, **kwargs) -> requests.Response:
        self._throttle()
        kwargs.setdefault("timeout", self.timeout_seconds)
        logger.debug("GET %s", url)
        response = self.session.get(url, **kwargs)
        self._last_request_ts = time.monotonic()
        response.raise_for_status()
        return response

    def post(self, url: str, **kwargs) -> requests.Response:
        self._throttle()
        kwargs.setdefault("timeout", self.timeout_seconds)
        logger.debug("POST %s data=%s", url, kwargs.get("data"))
        response = self.session.post(url, **kwargs)
        self._last_request_ts = time.monotonic()
        response.raise_for_status()
        return response
