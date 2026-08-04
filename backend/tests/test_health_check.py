import pytest

pytestmark = pytest.mark.django_db


def test_health_check_does_not_require_authentication(api_client):
    response = api_client.get("/api/v1/health/")
    assert response.status_code == 200


def test_health_check_reports_mongodb_ok(api_client):
    response = api_client.get("/api/v1/health/")
    body = response.json()
    assert body["status"] == "ok"
    assert body["mongodb"] is True


def test_metrics_endpoint_returns_prometheus_format(api_client):
    response = api_client.get("/metrics")
    assert response.status_code == 200
    body = response.content.decode()
    assert "# HELP" in body
    assert "# TYPE" in body


def test_metrics_endpoint_does_not_require_authentication(api_client):
    response = api_client.get("/metrics")
    assert response.status_code == 200
