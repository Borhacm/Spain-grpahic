from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.connectors.base import BaseConnector


class RegistradoresConnector(BaseConnector):
    source_slug = "registradores"
    base_url = "https://www.registradores.org"

    async def fetch(self, directory_url: str | None = None) -> Iterable[dict[str, Any]]:
        if not directory_url:
            return []
        payload = await self._get_json(directory_url)
        return payload if isinstance(payload, list) else [payload]
