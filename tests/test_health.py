def test_health_endpoint_reports_service_ready(env) -> None:
    response = env.client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_allows_local_frontend_origin(env) -> None:
    response = env.client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_health_endpoint_rejects_unsupported_methods(env) -> None:
    assert env.client.post("/health").status_code == 405
