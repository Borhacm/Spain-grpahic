from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


def test_health_endpoint(db_session) -> None:
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    app.dependency_overrides.clear()


def test_health_ops_endpoint(db_session) -> None:
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    client = TestClient(app)
    response = client.get("/health/ops")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "scheduler" in payload
    assert "locking" in payload
    app.dependency_overrides.clear()
