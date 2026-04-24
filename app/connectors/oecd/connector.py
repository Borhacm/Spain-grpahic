from __future__ import annotations

import csv
from collections.abc import Iterable
from io import StringIO
from typing import Any

from app.connectors.base import BaseConnector


class OECDConnector(BaseConnector):
    source_slug = "oecd"
    base_url = "https://sdmx.oecd.org/public/rest/data"

    def _resolve_code_to_path(self, code: str) -> str:
        """
        Supported code formats:
        - Compact: GOV_DGOGD_2025:DG:ESP
        - Full SDMX path: OECD.GOV.GIP,DSD_GOV@DF_GOV_DGOGD_2025,1.0/A.ESP.DG.IX._Z.2025.DGOGD
        """
        if "/" in code and "," in code:
            return code
        parts = [segment.strip() for segment in code.split(":")]
        if len(parts) == 3 and parts[0].upper() == "GOV_DGOGD_2025":
            measure = parts[1].upper()
            country = parts[2].upper()
            return f"OECD.GOV.GIP,DSD_GOV@DF_GOV_DGOGD_2025,1.0/A.{country}.{measure}.IX._Z.2025.DGOGD"
        raise ValueError(f"Unsupported OECD code format: {code}")

    async def fetch(self, code: str) -> Iterable[dict[str, Any]]:
        path = self._resolve_code_to_path(code)
        url = f"{self.base_url}/{path}"
        await self.limiter.acquire()
        response = await self.client.get(
            url,
            params={"format": "csvfilewithlabels"},
            headers={"User-Agent": "spain-graphic/1.0"},
        )
        response.raise_for_status()
        text = response.text
        reader = csv.DictReader(StringIO(text))
        return [row for row in reader]
