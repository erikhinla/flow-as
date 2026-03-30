from fastapi.testclient import TestClient

from app.main import app


def test_capabilities_endpoint_shape():
    client = TestClient(app)
    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert "registries" in payload
    assert "tasks" in payload["registries"]
    assert "artifacts" in payload["registries"]
    assert "handoffs" in payload["registries"]
    assert "threads" in payload["registries"]
    assert "agents" in payload["registries"]
    assert "runtime_state" in payload
    assert "redis" in payload["runtime_state"]
    assert "durable_memory" in payload
    assert "notion" in payload["durable_memory"]
