import pytest

from app.connectors.datosgob.connector import DatosGobConnector


@pytest.mark.asyncio
async def test_datosgob_connector_fetch_parses_items(monkeypatch) -> None:
    connector = DatosGobConnector()

    async def fake_get_json(url, params=None):
        return {"result": {"items": [{"_id": "abc", "title": "Dataset demo"}]}}

    monkeypatch.setattr(connector, "_get_json", fake_get_json)
    data = await connector.fetch(keyword="pib")
    assert len(data) == 1
    assert data[0]["_id"] == "abc"
    await connector.close()
