from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


def test_editorial_dashboard_endpoint(db_session) -> None:
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    client = TestClient(app)
    response = client.get("/editorial/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert "candidates_total" in payload
    app.dependency_overrides.clear()
