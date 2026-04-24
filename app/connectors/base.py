from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings


@dataclass(slots=True)
class RateLimiter:
    requests_per_second: float = 2.0
    _last_ts: float = 0.0

    async def acquire(self) -> None:
        import asyncio
        import time

        now = time.monotonic()
        min_delta = 1.0 / self.requests_per_second
        elapsed = now - self._last_ts
        if elapsed < min_delta:
            await asyncio.sleep(min_delta - elapsed)
        self._last_ts = time.monotonic()


class BaseConnector(ABC):
    source_slug: str
    base_url: str

    def __init__(self, timeout: float | None = None, limiter: RateLimiter | None = None) -> None:
        settings = get_settings()
        self.timeout = timeout or settings.request_timeout_seconds
        self.limiter = limiter or RateLimiter()
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self) -> None:
        await self.client.aclose()

    @retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3), reraise=True)
    async def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        await self.limiter.acquire()
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @abstractmethod
    async def fetch(self, **kwargs: Any) -> Iterable[dict[str, Any]]:
        raise NotImplementedError
