"""Tests for wormhole service main application."""
import pytest
from fastapi.testclient import TestClient


def test_health_endpoint():
    """Test that health endpoint returns OK."""
    from app.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_openapi_docs_available():
    """Test that OpenAPI docs are available."""
    from app.main import app
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200
