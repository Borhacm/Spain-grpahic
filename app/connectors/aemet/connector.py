from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.connectors.base import BaseConnector
from app.core.config import get_settings


class AEMETConnector(BaseConnector):
    source_slug = "aemet"
    base_url = "https://opendata.aemet.es/opendata/api"

    async def fetch(self, endpoint: str, params: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        settings = get_settings()
        if not settings.aemet_api_key:
            return []
        req_params = {"api_key": settings.aemet_api_key, **(params or {})}
        first = await self._get_json(f"{self.base_url}/{endpoint}", params=req_params)
        datos_url = first.get("datos")
        if not datos_url:
            return []
        data = await self._get_json(datos_url)
        if isinstance(data, list):
            return data
        return [data]
