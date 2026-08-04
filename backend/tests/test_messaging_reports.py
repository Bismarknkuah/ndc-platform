import pytest

pytestmark = pytest.mark.django_db


def test_branch_officer_can_report_to_constituency(
    branch_reporter_client, constituency_unit
):
    response = branch_reporter_client.post(
        "/api/v1/messaging/reports/",
        {
            "title": "Voter registration update",
            "body": "1,200 new voters registered this week.",
            "target_unit_id": str(constituency_unit.id),
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["submitting_unit"]["unit_type"] == "BRANCH"
    assert response.json()["target_unit"]["unit_type"] == "CONSTITUENCY"


def test_branch_officer_can_report_all_the_way_to_national(
    branch_reporter_client, national_unit
):
    response = branch_reporter_client.post(
        "/api/v1/messaging/reports/",
        {
            "title": "Urgent incident report",
            "body": "Details of the incident.",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 201


def test_cannot_report_to_a_non_ancestor_unit(branch_reporter_client, national_unit):
    from apps.hierarchy.documents import OrganizationalUnit

    unrelated_region = OrganizationalUnit.objects.create(
        name="Volta Region",
        code="ndc-volta-report-test",
        unit_type="REGIONAL",
        parent=national_unit,
    )
    response = branch_reporter_client.post(
        "/api/v1/messaging/reports/",
        {
            "title": "Bad report",
            "body": "Body.",
            "target_unit_id": str(unrelated_region.id),
        },
        format="json",
    )
    assert response.status_code == 400


def test_member_without_reporting_permission_cannot_submit(auth_client, national_unit):
    response = auth_client.post(
        "/api/v1/messaging/reports/",
        {
            "title": "Blocked report",
            "body": "Body.",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 403


def test_target_office_can_acknowledge_report(
    branch_reporter_client, constituency_unit, ordinary_role
):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import User
    from rest_framework.test import APIClient

    created = branch_reporter_client.post(
        "/api/v1/messaging/reports/",
        {
            "title": "Report",
            "body": "Body.",
            "target_unit_id": str(constituency_unit.id),
        },
        format="json",
    ).json()

    constituency_officer = User(
        email="constituency@example.com",
        phone_number="0244000060",
        first_name="Efua",
        last_name="Officer",
        membership_id="NDC-TEST-000060",
        organizational_unit=constituency_unit,
        role=ordinary_role,
    )
    constituency_officer.set_password("StrongPass123!")
    constituency_officer.save()

    client = APIClient()
    tokens = issue_token_pair(constituency_officer)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.patch(
        f"/api/v1/messaging/reports/{created['id']}/",
        {"status": "ACKNOWLEDGED"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ACKNOWLEDGED"


def test_unrelated_user_cannot_resolve_report(
    branch_reporter_client, constituency_unit, auth_client
):
    created = branch_reporter_client.post(
        "/api/v1/messaging/reports/",
        {
            "title": "Report",
            "body": "Body.",
            "target_unit_id": str(constituency_unit.id),
        },
        format="json",
    ).json()
    response = auth_client.patch(
        f"/api/v1/messaging/reports/{created['id']}/",
        {"status": "RESOLVED"},
        format="json",
    )
    assert response.status_code == 403


def test_reporter_can_view_own_report(branch_reporter_client, constituency_unit):
    created = branch_reporter_client.post(
        "/api/v1/messaging/reports/",
        {
            "title": "Report",
            "body": "Body.",
            "target_unit_id": str(constituency_unit.id),
        },
        format="json",
    ).json()
    response = branch_reporter_client.get(f"/api/v1/messaging/reports/{created['id']}/")
    assert response.status_code == 200
