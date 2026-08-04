import base64

import pytest

pytestmark = pytest.mark.django_db

_FAKE_FILE = base64.b64encode(b"fake-pdf-bytes").decode("ascii")


def test_authorized_officer_can_upload_document(chairman_client, national_unit):
    response = chairman_client.post(
        "/api/v1/documents/",
        {
            "title": "Party Constitution",
            "category": "CONSTITUTION",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_FILE,
            "file_name": "constitution.pdf",
            "mime_type": "application/pdf",
            "is_public_within_party": True,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["file_base64"] == _FAKE_FILE


def test_ordinary_member_cannot_upload_document(auth_client, national_unit):
    response = auth_client.post(
        "/api/v1/documents/",
        {
            "title": "Should fail",
            "category": "OTHER",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_FILE,
            "file_name": "x.pdf",
            "mime_type": "application/pdf",
        },
        format="json",
    )
    assert response.status_code == 403


def test_oversized_file_rejected(chairman_client, national_unit):
    response = chairman_client.post(
        "/api/v1/documents/",
        {
            "title": "Huge file",
            "category": "OTHER",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": "A" * 8_000_000,
            "file_name": "huge.pdf",
            "mime_type": "application/pdf",
        },
        format="json",
    )
    assert response.status_code == 400


def test_public_document_visible_to_any_member(
    chairman_client, auth_client, national_unit
):
    chairman_client.post(
        "/api/v1/documents/",
        {
            "title": "Public Policy",
            "category": "POLICY",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_FILE,
            "file_name": "policy.pdf",
            "mime_type": "application/pdf",
            "is_public_within_party": True,
        },
        format="json",
    )
    response = auth_client.get("/api/v1/documents/")
    titles = [d["title"] for d in response.json()["results"]]
    assert "Public Policy" in titles


def test_list_view_omits_file_payload(chairman_client, national_unit):
    chairman_client.post(
        "/api/v1/documents/",
        {
            "title": "Doc",
            "category": "OTHER",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_FILE,
            "file_name": "x.pdf",
            "mime_type": "application/pdf",
            "is_public_within_party": True,
        },
        format="json",
    )
    response = chairman_client.get("/api/v1/documents/")
    assert "file_base64" not in response.json()["results"][0]


def test_detail_view_includes_file_payload(chairman_client, national_unit):
    created = chairman_client.post(
        "/api/v1/documents/",
        {
            "title": "Doc",
            "category": "OTHER",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_FILE,
            "file_name": "x.pdf",
            "mime_type": "application/pdf",
        },
        format="json",
    ).json()
    response = chairman_client.get(f"/api/v1/documents/{created['id']}/")
    assert response.json()["file_base64"] == _FAKE_FILE


def test_non_public_document_hidden_from_unrelated_unit(
    chairman_client, national_unit, branch_unit
):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from apps.hierarchy.documents import OrganizationalUnit
    from rest_framework.test import APIClient

    other_region = OrganizationalUnit.objects.create(
        name="Volta Region",
        code="ndc-volta-doc-test",
        unit_type="REGIONAL",
        parent=national_unit,
    )
    role = Role.objects.create(
        name="Member", code="doc_test_role", scope="REGIONAL", permissions=[]
    )
    outsider = User(
        email="outsider-doc@example.com",
        phone_number="0244001000",
        first_name="Out",
        last_name="Sider",
        membership_id="NDC-TEST-001000",
        organizational_unit=other_region,
        role=role,
    )
    outsider.set_password("StrongPass123!")
    outsider.save()
    client = APIClient()
    tokens = issue_token_pair(outsider)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    created = chairman_client.post(
        "/api/v1/documents/",
        {
            "title": "Branch-only doc",
            "category": "MINUTES",
            "organizational_unit_id": str(branch_unit.id),
            "file_base64": _FAKE_FILE,
            "file_name": "x.pdf",
            "mime_type": "application/pdf",
            "is_public_within_party": False,
        },
        format="json",
    ).json()

    response = client.get(f"/api/v1/documents/{created['id']}/")
    assert response.status_code == 403


def test_ancestor_unit_member_can_view_descendant_document(
    chairman_client, branch_unit
):
    created = chairman_client.post(
        "/api/v1/documents/",
        {
            "title": "Branch minutes",
            "category": "MINUTES",
            "organizational_unit_id": str(branch_unit.id),
            "file_base64": _FAKE_FILE,
            "file_name": "x.pdf",
            "mime_type": "application/pdf",
        },
        format="json",
    ).json()
    # chairman_client is at National, an ancestor of the branch.
    response = chairman_client.get(f"/api/v1/documents/{created['id']}/")
    assert response.status_code == 200


def test_authority_can_delete_document(chairman_client, national_unit):
    created = chairman_client.post(
        "/api/v1/documents/",
        {
            "title": "Doc",
            "category": "OTHER",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_FILE,
            "file_name": "x.pdf",
            "mime_type": "application/pdf",
        },
        format="json",
    ).json()
    response = chairman_client.delete(f"/api/v1/documents/{created['id']}/")
    assert response.status_code == 204

    follow_up = chairman_client.get(f"/api/v1/documents/{created['id']}/")
    assert follow_up.status_code == 404
