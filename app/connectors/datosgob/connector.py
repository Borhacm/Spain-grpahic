from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.connectors.base import BaseConnector


class DatosGobConnector(BaseConnector):
    source_slug = "datosgob"
    base_url = "https://datos.gob.es/apidata/catalog/dataset"

    async def fetch(
        self,
        keyword: str | None = None,
        theme: str | None = None,
        organization: str | None = None,
        page: int = 1,
        items_per_page: int = 50,
    ) -> Iterable[dict[str, Any]]:
        params: dict[str, Any] = {"_page": page, "_items_per_page": items_per_page}
        if keyword:
            params["title"] = keyword
        if theme:
            params["theme"] = theme
        if organization:
            params["publisher"] = organization
        payload = await self._get_json(self.base_url, params=params)
        datasets = payload.get("result", {}).get("items", [])
        return datasets
