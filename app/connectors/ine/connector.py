from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.connectors.base import BaseConnector


class INEConnector(BaseConnector):
    source_slug = "ine"
    base_url = "https://servicios.ine.es/wstempus/js/ES"

    async def fetch(
        self,
        code: str | None = None,
        table: str | None = None,
    ) -> Iterable[dict[str, Any]]:
        if code:
            # INE requires nult/date query params for DATOS_SERIE in many series codes.
            data = await self._get_json(f"{self.base_url}/DATOS_SERIE/{code}?nult=300")
            series_data = data if isinstance(data, list) else [data]
            return series_data
        if table:
            data = await self._get_json(f"{self.base_url}/DATOS_TABLA/{table}")
            return data if isinstance(data, list) else [data]
        operations = await self._get_json(f"{self.base_url}/OPERACIONES_DISPONIBLES")
        return operations if isinstance(operations, list) else [operations]
