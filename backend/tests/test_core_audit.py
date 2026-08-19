import pytest

from apps.core.audit import AuditLog, log_action

pytestmark = pytest.mark.django_db


def test_log_action_persists_entry(member_user):
    entry = log_action(member_user, "test.action", description="did a thing")
    assert AuditLog.objects.count() == 1
    stored = AuditLog.objects.first()
    assert str(stored.id) == str(entry.id)
    assert stored.action == "test.action"
    assert stored.actor_email == member_user.email


def test_login_writes_audit_entry(api_client, member_user):
    api_client.post(
        "/api/v1/auth/login/",
        {"email": member_user.email, "password": "StrongPass123!"},
        format="json",
    )
    assert (
        AuditLog.objects(action="user.login", actor_email=member_user.email).count()
        == 1
    )


def test_ordinary_member_cannot_view_audit_log(auth_client):
    response = auth_client.get("/api/v1/audit/logs/")
    assert response.status_code == 403


def test_national_chairman_can_view_audit_log(chairman_client, national_chairman_user):
    log_action(national_chairman_user, "hierarchy.unit.create", description="seed data")
    response = chairman_client.get("/api/v1/audit/logs/")
    assert response.status_code == 200
    assert response.json()["count"] >= 1
