"""Tests for health check endpoint."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_endpoint_returns_200() -> None:
    """Test that health endpoint returns 200 status code."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_returns_correct_body() -> None:
    """Test that health endpoint returns correct response body."""
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_health_endpoint_with_trailing_slash() -> None:
    """Test that health endpoint handles trailing slash."""
    response = client.get("/health/")
    # FastAPI redirects /health/ to /health, so we accept both 200 and 307
    assert response.status_code in [200, 307]
