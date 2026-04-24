from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.connectors.base import BaseConnector


class FMIConnector(BaseConnector):
    source_slug = "fmi"
    base_url = "https://www.imf.org/external/datamapper/api/v2"

    async def fetch(self, code: str, country: str = "ESP") -> Iterable[dict[str, Any]]:
        indicator = (code or "").strip().upper()
        country_code = (country or "ESP").strip().upper()
        if not indicator:
            raise ValueError("FMI indicator code is required")
        if not country_code:
            raise ValueError("FMI country code is required")

        payload = await self._get_json(f"{self.base_url}/{indicator}/{country_code}")
        values = (
            payload.get("values", {})
            .get(indicator, {})
            .get(country_code, {})
        )
        if not isinstance(values, dict):
            return []

        rows: list[dict[str, Any]] = []
        for period, value in values.items():
            rows.append(
                {
                    "INDICATOR": indicator,
                    "REF_AREA": country_code,
                    "TIME_PERIOD": str(period),
                    "OBS_VALUE": value,
                }
            )
        return rows
