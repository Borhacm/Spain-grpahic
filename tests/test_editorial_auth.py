from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app


def test_editorial_auth_requires_api_key_when_configured(db_session, monkeypatch) -> None:
    monkeypatch.setenv("API_KEYS", "viewer-token:viewer,editor-token:editor,admin-token:admin")
    get_settings.cache_clear()

    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    client = TestClient(app)

    no_key_response = client.get("/editorial/dashboard")
    assert no_key_response.status_code == 401

    viewer_response = client.get("/editorial/dashboard", headers={"x-api-key": "viewer-token"})
    assert viewer_response.status_code == 200

    forbidden_response = client.post("/signals/run", headers={"x-api-key": "viewer-token"})
    assert forbidden_response.status_code == 403

    allowed_response = client.post("/signals/run", headers={"x-api-key": "editor-token"})
    assert allowed_response.status_code not in (401, 403)

    app.dependency_overrides.clear()
    monkeypatch.delenv("API_KEYS", raising=False)
    get_settings.cache_clear()
