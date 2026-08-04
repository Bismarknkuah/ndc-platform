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
