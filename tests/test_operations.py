from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.main import app


def test_liveness(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_readiness_with_database(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "UP"


class _BrokenSession:
    def execute(self, *_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    def get(self, *_args, **_kwargs):
        raise OperationalError("SELECT", {}, Exception("connection refused"))


def test_database_outage(client: TestClient) -> None:
    app.dependency_overrides[get_db] = lambda: _BrokenSession()

    ready = client.get("/health/ready")
    assert ready.status_code == 503
    assert ready.json()["database"] == "DOWN"

    # Liveness ignores the database on purpose.
    assert client.get("/health/live").status_code == 200

    response = client.get(f"/api/v1/modules/{uuid4()}")
    assert response.status_code == 503
    assert response.json()["code"] == "DATABASE_UNAVAILABLE"


def test_metrics_use_route_templates(client: TestClient, module: dict) -> None:
    client.get(f"/api/v1/modules/{module['id']}")
    client.get(f"/api/v1/modules/{uuid4()}")
    client.get("/does-not-exist")
    client.get("/health/live")

    body = client.get("/metrics").text
    assert (
        'http_requests_total{method="GET",path="/api/v1/modules/{module_id}",status="200"}' in body
    )
    assert (
        'http_requests_total{method="GET",path="/api/v1/modules/{module_id}",status="404"}' in body
    )
    assert 'path="<unmatched>",status="404"' in body
    assert "http_request_duration_seconds_bucket" in body
    # Probes and scrapes are not counted.
    assert 'path="/health/live"' not in body
    assert 'path="/metrics"' not in body
    assert module["id"] not in body
