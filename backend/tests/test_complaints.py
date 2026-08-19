import pytest

pytestmark = pytest.mark.django_db


def test_member_can_submit_complaint_to_ancestor_unit(auth_client, constituency_unit):
    response = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "COMPLAINT",
            "subject": "Branch meeting irregularities",
            "description": "The branch chairman did not follow proper procedure.",
            "target_unit_id": str(constituency_unit.id),
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "SUBMITTED"


def test_cannot_address_complaint_to_non_ancestor_unit(auth_client, national_unit):
    from apps.hierarchy.documents import OrganizationalUnit

    unrelated_region = OrganizationalUnit.objects.create(
        name="Volta Region",
        code="ndc-volta-complaint-test",
        unit_type="REGIONAL",
        parent=national_unit,
    )
    response = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "COMPLAINT",
            "subject": "Bad complaint",
            "description": "Should fail.",
            "target_unit_id": str(unrelated_region.id),
        },
        format="json",
    )
    assert response.status_code == 400


def test_petition_can_be_submitted(auth_client, national_unit):
    response = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "PETITION",
            "subject": "Request for new polling station",
            "description": "We need a closer polling station for our community.",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["complaint_type"] == "PETITION"


def test_members_can_cosign_petition(auth_client, chairman_client, national_unit):
    petition = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "PETITION",
            "subject": "New polling station",
            "description": "Need one closer.",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    response = chairman_client.post(f"/api/v1/complaints/{petition['id']}/support/")
    assert response.status_code == 201
    assert response.json()["supporter_count"] == 1


def test_cosigning_twice_does_not_double_count(
    auth_client, chairman_client, national_unit
):
    petition = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "PETITION",
            "subject": "New polling station",
            "description": "Need one closer.",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    chairman_client.post(f"/api/v1/complaints/{petition['id']}/support/")
    second = chairman_client.post(f"/api/v1/complaints/{petition['id']}/support/")
    assert second.json()["already_signed"] is True
    assert second.json()["supporter_count"] == 1


def test_cannot_cosign_a_plain_complaint(auth_client, chairman_client, national_unit):
    complaint = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "COMPLAINT",
            "subject": "Issue",
            "description": "Some issue.",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    response = chairman_client.post(f"/api/v1/complaints/{complaint['id']}/support/")
    assert response.status_code == 400


def test_authority_can_assign_and_resolve_complaint(
    chairman_client, auth_client, national_unit, national_chairman_user
):
    complaint = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "COMPLAINT",
            "subject": "Issue",
            "description": "Some issue.",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    assign = chairman_client.patch(
        f"/api/v1/complaints/{complaint['id']}/",
        {"assigned_to_id": str(national_chairman_user.id), "status": "UNDER_REVIEW"},
        format="json",
    )
    assert assign.status_code == 200
    assert assign.json()["assigned_to"]["id"] == str(national_chairman_user.id)

    resolve = chairman_client.patch(
        f"/api/v1/complaints/{complaint['id']}/",
        {
            "status": "RESOLVED",
            "resolution_notes": "Addressed with the branch chairman.",
        },
        format="json",
    )
    assert resolve.json()["status"] == "RESOLVED"
    assert resolve.json()["resolved_by"] is not None


def test_unrelated_member_cannot_manage_complaint(
    auth_client, national_unit, member_user
):
    complaint = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "COMPLAINT",
            "subject": "Issue",
            "description": "Some issue.",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    response = auth_client.patch(
        f"/api/v1/complaints/{complaint['id']}/", {"status": "RESOLVED"}, format="json"
    )
    assert response.status_code == 403


def test_submitter_can_view_own_complaint(auth_client, national_unit):
    complaint = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "COMPLAINT",
            "subject": "Issue",
            "description": "Some issue.",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    response = auth_client.get(f"/api/v1/complaints/{complaint['id']}/")
    assert response.status_code == 200


def test_anonymous_report_hides_reporter_name_from_ordinary_viewers(
    chairman_client, auth_client, member_user, national_unit
):
    """The core anonymity guarantee: an anonymous accountability report
    shows "Anonymous" to a viewer without reveal authority, even one
    with real complaint-management authority over the target unit."""
    create = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "ACCOUNTABILITY_REPORT",
            "subject": "Misuse of branch funds",
            "description": "Funds collected for the fundraiser were not accounted for.",
            "target_unit_id": str(national_unit.id),
            "is_anonymous": True,
        },
        format="json",
    )
    assert create.status_code == 201
    complaint_id = create.json()["id"]
    assert create.json()["submitted_by"]["full_name"] == member_user.full_name

    # A regular complaint-management viewer (not top leadership) sees
    # "Anonymous", not the real name.
    from apps.accounts.documents import Role, User
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_anon_test",
        scope="REGIONAL",
        is_executive=True,
        permissions=["hierarchy.manage"],
    )
    regional_exec = User(
        email="regional-anon@example.com",
        phone_number="0244000092",
        first_name="Regional",
        last_name="Anon",
        membership_id="NDC-TEST-000092",
        organizational_unit=national_unit,
        role=role,
    )
    regional_exec.set_password("StrongPass123!")
    regional_exec.save()
    tokens = issue_token_pair(regional_exec)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get(f"/api/v1/complaints/{complaint_id}/")
    assert response.status_code == 200
    body = response.json()
    assert body["submitted_by"]["full_name"] == "Anonymous"
    assert body["submitted_by"]["id"] is None


def test_top_leadership_can_reveal_anonymous_reporter_identity(
    chairman_client, auth_client, member_user, national_unit
):
    """chairman_client holds analytics.ground_intelligence (real
    National Chairman authority) - they see the real name."""
    create = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "ACCOUNTABILITY_REPORT",
            "subject": "Misuse of branch funds",
            "description": "Funds collected for the fundraiser were not accounted for.",
            "target_unit_id": str(national_unit.id),
            "is_anonymous": True,
        },
        format="json",
    )
    complaint_id = create.json()["id"]

    response = chairman_client.get(f"/api/v1/complaints/{complaint_id}/")
    assert response.status_code == 200
    assert response.json()["submitted_by"]["full_name"] == member_user.full_name


def test_submitter_always_sees_their_own_real_name_on_own_anonymous_submission(
    auth_client, member_user, national_unit
):
    create = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "ACCOUNTABILITY_REPORT",
            "subject": "Test",
            "description": "Test description.",
            "target_unit_id": str(national_unit.id),
            "is_anonymous": True,
        },
        format="json",
    )
    assert create.json()["submitted_by"]["full_name"] == member_user.full_name

    response = auth_client.get(f"/api/v1/complaints/{create.json()['id']}/")
    assert response.json()["submitted_by"]["full_name"] == member_user.full_name


def test_reported_executive_can_view_the_report_filed_against_them(
    chairman_client, auth_client, national_unit, national_chairman_user
):
    """Due process: the person a report is about can see what they're
    accused of, even though they can't see who filed it (unless they
    also separately hold reveal authority)."""
    create = auth_client.post(
        "/api/v1/complaints/",
        {
            "complaint_type": "ACCOUNTABILITY_REPORT",
            "subject": "Concern about conduct at the last meeting",
            "description": "Description here.",
            "target_unit_id": str(national_unit.id),
            "reported_user_id": str(national_chairman_user.id),
            "is_anonymous": True,
        },
        format="json",
    )
    assert create.status_code == 201

    response = chairman_client.get(f"/api/v1/complaints/{create.json()['id']}/")
    assert response.status_code == 200
    assert response.json()["reported_user"]["id"] == str(national_chairman_user.id)
