from fastapi.testclient import TestClient

from app.main import app


def test_liveness_endpoint_is_public_and_does_not_require_database():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("x-request-id")
