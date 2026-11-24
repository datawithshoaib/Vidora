
from fastapi.testclient import TestClient

from api.main import app


def test_health_endpoint_reports_service_ready() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_allows_local_frontend_origin() -> None:
    response = TestClient(app).get(
        "/health", headers={"Origin": "http://localhost:3000"}
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_health_endpoint_rejects_unsupported_methods() -> None:
    assert TestClient(app).post("/health").status_code == 405
