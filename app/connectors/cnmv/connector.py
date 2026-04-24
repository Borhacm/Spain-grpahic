from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.connectors.base import BaseConnector


class CNMVConnector(BaseConnector):
    source_slug = "cnmv"
    base_url = "https://www.cnmv.es"

    async def fetch(self, registry_url: str | None = None) -> Iterable[dict[str, Any]]:
        if not registry_url:
            return []
        # Adapter placeholder for prudent HTML/CSV parsing.
        payload = await self._get_json(registry_url)
        return payload if isinstance(payload, list) else [payload]
