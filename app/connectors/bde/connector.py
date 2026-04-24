from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.connectors.base import BaseConnector


class BDEConnector(BaseConnector):
    source_slug = "bde"
    base_url = "https://app.bde.es/bierest/resources/srdatosapp"

    async def fetch(self, code: str) -> Iterable[dict[str, Any]]:
        # New BdE API: listaSeries returns metadata + aligned arrays (fechas, valores).
        payload = await self._get_json(
            f"{self.base_url}/listaSeries",
            params={"idioma": "es", "series": code, "rango": "MAX"},
        )
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict) and isinstance(first.get("fechas"), list) and isinstance(first.get("valores"), list):
                rows: list[dict[str, Any]] = []
                for date_value, obs_value in zip(first["fechas"], first["valores"], strict=False):
                    rows.append({"date": date_value, "value": obs_value})
                if rows:
                    return rows
        data = payload.get("data") if isinstance(payload, dict) else payload
        if isinstance(data, list):
            return data
        if isinstance(payload, list):
            return payload
        return [payload]
