from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.connectors.base import BaseConnector


class BMEConnector(BaseConnector):
    source_slug = "bme"
    base_url = "https://www.bolsasymercados.es"

    async def fetch(self, listings_url: str | None = None) -> Iterable[dict[str, Any]]:
        if not listings_url:
            return []
        payload = await self._get_json(listings_url)
        return payload if isinstance(payload, list) else [payload]
