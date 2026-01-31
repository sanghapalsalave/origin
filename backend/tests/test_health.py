"""
Test health check endpoint.
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test that health check endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["service"] == "origin-backend"


def test_root_endpoint(client: TestClient):
    """Test that root endpoint returns API information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data
