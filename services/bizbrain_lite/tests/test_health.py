from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_shape():
    client = TestClient(app)
    response = client.get("/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "bizbrain-lite"
