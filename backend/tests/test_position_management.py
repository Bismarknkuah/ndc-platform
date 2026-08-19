"""
Tests for the Position Management Module (Role CRUD, reporting-chain
validation, and the scope-hardened can_manage_roles authority check) and
the member admin actions (search/list, suspend/reactivate, transfer)
added for the frontend build.
"""

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def regional_role_with_manage_roles(regional_unit):
    """A REGIONAL-scope role that (perhaps mistakenly) carries
    hierarchy.manage_roles - used to prove that scope alone doesn't grant
    Position Management Module authority; only National-level holders of
    that permission may manage the global Role catalog."""
    from apps.accounts.documents import Role

    return Role.objects.create(
        name="Regional Chairman (manage_roles test)",
        code="regional_chairman_manage_roles_test",
        scope="REGIONAL",
        permissions=["hierarchy.manage", "hierarchy.manage_roles"],
    )


@pytest.fixture
def regional_officer_client(regional_unit, regional_role_with_manage_roles):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import User
    from rest_framework.test import APIClient

    user = User(
        email="regional-officer-role-test@example.com",
        phone_number="0244002000",
        first_name="Regional",
        last_name="Officer",
        membership_id="NDC-TEST-002000",
        organizational_unit=regional_unit,
        role=regional_role_with_manage_roles,
    )
    user.set_password("StrongPass123!")
    user.save()
    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


# ---------------------------------------------------------------------------
# Role CRUD (Position Management Module)
# ---------------------------------------------------------------------------


def test_national_chairman_can_create_position(chairman_client):
    response = chairman_client.post(
        "/api/v1/auth/roles/",
        {
            "name": "Deputy Regional Communications Director",
            "code": "deputy_regional_comms_director",
            "scope": "REGIONAL",
            "is_executive": True,
            "permissions": ["messaging.broadcast.downward"],
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["code"] == "deputy_regional_comms_director"


def test_ordinary_member_cannot_create_position(auth_client):
    response = auth_client.post(
        "/api/v1/auth/roles/",
        {"name": "Should fail", "code": "should_fail_role", "scope": "BRANCH"},
        format="json",
    )
    assert response.status_code == 403


def test_regional_scope_holder_of_manage_roles_cannot_create_position(
    regional_officer_client,
):
    """The hardening: hierarchy.manage_roles alone isn't enough - must be
    held by a NATIONAL-scope user, since Role objects are global."""
    response = regional_officer_client.post(
        "/api/v1/auth/roles/",
        {
            "name": "Should still fail",
            "code": "should_still_fail_role",
            "scope": "BRANCH",
        },
        format="json",
    )
    assert response.status_code == 403


def test_duplicate_role_code_rejected(chairman_client):
    chairman_client.post(
        "/api/v1/auth/roles/",
        {"name": "First", "code": "dup_code_test", "scope": "BRANCH"},
        format="json",
    )
    response = chairman_client.post(
        "/api/v1/auth/roles/",
        {"name": "Second", "code": "dup_code_test", "scope": "BRANCH"},
        format="json",
    )
    assert response.status_code == 400


def test_national_chairman_can_update_position(chairman_client):
    created = chairman_client.post(
        "/api/v1/auth/roles/",
        {"name": "Original Name", "code": "update_test_role", "scope": "BRANCH"},
        format="json",
    ).json()
    response = chairman_client.patch(
        f"/api/v1/auth/roles/{created['id']}/",
        {"name": "Renamed Position", "permissions": ["membership.register"]},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Position"
    assert response.json()["permissions"] == ["membership.register"]


def test_regional_scope_holder_cannot_update_position(
    chairman_client, regional_officer_client
):
    created = chairman_client.post(
        "/api/v1/auth/roles/",
        {"name": "Untouchable", "code": "untouchable_role_test", "scope": "BRANCH"},
        format="json",
    ).json()
    response = regional_officer_client.patch(
        f"/api/v1/auth/roles/{created['id']}/", {"name": "Hijacked"}, format="json"
    )
    assert response.status_code == 403


def test_any_authenticated_user_can_browse_roles(auth_client):
    response = auth_client.get("/api/v1/auth/roles/")
    assert response.status_code == 200


def test_reports_to_self_reference_rejected(chairman_client):
    created = chairman_client.post(
        "/api/v1/auth/roles/",
        {"name": "Self Reporter", "code": "self_reporter_role_test", "scope": "BRANCH"},
        format="json",
    ).json()
    response = chairman_client.patch(
        f"/api/v1/auth/roles/{created['id']}/",
        {"reports_to_id": created["id"]},
        format="json",
    )
    assert response.status_code == 400


def test_circular_reporting_chain_rejected(chairman_client):
    role_a = chairman_client.post(
        "/api/v1/auth/roles/",
        {"name": "Role A", "code": "circular_role_a_test", "scope": "BRANCH"},
        format="json",
    ).json()
    role_b = chairman_client.post(
        "/api/v1/auth/roles/",
        {
            "name": "Role B",
            "code": "circular_role_b_test",
            "scope": "BRANCH",
            "reports_to_id": role_a["id"],
        },
        format="json",
    ).json()
    # Now try to make A report to B, which already reports to A - a cycle.
    response = chairman_client.patch(
        f"/api/v1/auth/roles/{role_a['id']}/",
        {"reports_to_id": role_b["id"]},
        format="json",
    )
    assert response.status_code == 400


def test_valid_reporting_chain_accepted(chairman_client):
    parent = chairman_client.post(
        "/api/v1/auth/roles/",
        {
            "name": "Parent Position",
            "code": "valid_chain_parent_test",
            "scope": "REGIONAL",
        },
        format="json",
    ).json()
    response = chairman_client.post(
        "/api/v1/auth/roles/",
        {
            "name": "Child Position",
            "code": "valid_chain_child_test",
            "scope": "CONSTITUENCY",
            "reports_to_id": parent["id"],
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["reports_to"]["id"] == parent["id"]


def test_national_chairman_can_retire_unused_position(chairman_client):
    created = chairman_client.post(
        "/api/v1/auth/roles/",
        {"name": "Unused Position", "code": "unused_role_test", "scope": "BRANCH"},
        format="json",
    ).json()
    response = chairman_client.delete(f"/api/v1/auth/roles/{created['id']}/")
    assert response.status_code == 204

    follow_up = chairman_client.get(f"/api/v1/auth/roles/{created['id']}/")
    assert follow_up.status_code == 404


def test_cannot_retire_position_held_by_active_member(chairman_client, branch_unit):
    from apps.accounts.documents import User

    created = chairman_client.post(
        "/api/v1/auth/roles/",
        {"name": "Occupied Position", "code": "occupied_role_test", "scope": "BRANCH"},
        format="json",
    ).json()

    from apps.accounts.documents import Role

    role = Role.objects.get(id=created["id"])
    holder = User(
        email="role-holder@example.com",
        phone_number="0244003000",
        first_name="Role",
        last_name="Holder",
        membership_id="NDC-TEST-003000",
        organizational_unit=branch_unit,
        role=role,
    )
    holder.set_password("StrongPass123!")
    holder.save()

    response = chairman_client.delete(f"/api/v1/auth/roles/{created['id']}/")
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Member search/list
# ---------------------------------------------------------------------------


def test_authority_can_list_members_in_jurisdiction(
    chairman_client, national_unit, member_user
):
    response = chairman_client.get(
        f"/api/v1/auth/members/list/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200
    assert response.json()["count"] >= 1


def test_member_list_defaults_to_own_unit_when_no_param(chairman_client):
    response = chairman_client.get("/api/v1/auth/members/list/")
    assert response.status_code == 200


def test_ordinary_member_cannot_browse_member_list(auth_client, national_unit):
    response = auth_client.get(
        f"/api/v1/auth/members/list/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 403


def test_member_search_by_name(chairman_client, national_unit, member_user):
    response = chairman_client.get(
        f"/api/v1/auth/members/list/?organizational_unit_id={national_unit.id}&search={member_user.first_name}"
    )
    assert response.status_code == 200
    membership_ids = [m["membership_id"] for m in response.json()["results"]]
    assert member_user.membership_id in membership_ids


def test_member_search_no_match_returns_empty(chairman_client, national_unit):
    response = chairman_client.get(
        f"/api/v1/auth/members/list/?organizational_unit_id={national_unit.id}&search=NoSuchPersonXYZ"
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_member_list_filters_by_active_status(
    chairman_client, national_unit, member_user
):
    response = chairman_client.get(
        f"/api/v1/auth/members/list/?organizational_unit_id={national_unit.id}&is_active=true"
    )
    assert response.status_code == 200
    assert all(m["is_active"] for m in response.json()["results"])


# ---------------------------------------------------------------------------
# Member detail / suspend / reactivate
# ---------------------------------------------------------------------------


def test_member_can_view_own_profile(auth_client, member_user):
    response = auth_client.get(f"/api/v1/auth/members/{member_user.id}/")
    assert response.status_code == 200


def test_unrelated_member_cannot_view_another_profile(
    auth_client, national_chairman_user
):
    response = auth_client.get(f"/api/v1/auth/members/{national_chairman_user.id}/")
    assert response.status_code == 403


def test_authority_can_view_member_in_jurisdiction(chairman_client, member_user):
    response = chairman_client.get(f"/api/v1/auth/members/{member_user.id}/")
    assert response.status_code == 200


def test_authority_can_suspend_member(chairman_client, member_user):
    response = chairman_client.patch(
        f"/api/v1/auth/members/{member_user.id}/",
        {"is_active": False, "deactivation_reason": "Requested by member"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_authority_can_reactivate_member(chairman_client, member_user):
    chairman_client.patch(
        f"/api/v1/auth/members/{member_user.id}/", {"is_active": False}, format="json"
    )
    response = chairman_client.patch(
        f"/api/v1/auth/members/{member_user.id}/", {"is_active": True}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_ordinary_member_cannot_suspend_others(auth_client, national_chairman_user):
    response = auth_client.patch(
        f"/api/v1/auth/members/{national_chairman_user.id}/",
        {"is_active": False},
        format="json",
    )
    assert response.status_code == 403


def test_authority_can_correct_member_profile_data(chairman_client, member_user):
    response = chairman_client.patch(
        f"/api/v1/auth/members/{member_user.id}/",
        {"national_id_number": "GHA-999999999-1"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["national_id_number"] == "GHA-999999999-1"


# ---------------------------------------------------------------------------
# Member transfer
# ---------------------------------------------------------------------------


def test_authority_over_both_units_can_transfer_member(
    chairman_client, member_user, national_unit
):
    from apps.hierarchy.documents import OrganizationalUnit

    other_region = OrganizationalUnit.objects.create(
        name="Volta Region",
        code="ndc-volta-transfer-test",
        unit_type="REGIONAL",
        parent=national_unit,
    )
    response = chairman_client.post(
        f"/api/v1/auth/members/{member_user.id}/transfer/",
        {"target_organizational_unit_id": str(other_region.id), "reason": "Relocated"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["organizational_unit"]["id"] == str(other_region.id)


def test_transfer_requires_authority_over_destination(
    member_user, branch_unit, national_unit
):
    """A constituency-level officer with authority over the member's
    current branch, but not over an unrelated destination unit, cannot
    complete the transfer."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from apps.hierarchy.documents import OrganizationalUnit
    from rest_framework.test import APIClient

    constituency_unit = (
        branch_unit.parent
    )  # branch -> constituency (Article 11: 4 levels)
    role = Role.objects.create(
        name="Constituency Chairman (transfer test)",
        code="constituency_chairman_transfer_test",
        scope="CONSTITUENCY",
        permissions=["hierarchy.manage"],
    )
    officer = User(
        email="constituency-transfer-test@example.com",
        phone_number="0244004000",
        first_name="Constituency",
        last_name="Officer",
        membership_id="NDC-TEST-004000",
        organizational_unit=constituency_unit,
        role=role,
    )
    officer.set_password("StrongPass123!")
    officer.save()
    client = APIClient()
    tokens = issue_token_pair(officer)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    unrelated_region = OrganizationalUnit.objects.create(
        name="Unrelated Region",
        code="ndc-unrelated-transfer-test",
        unit_type="REGIONAL",
        parent=national_unit,
    )
    response = client.post(
        f"/api/v1/auth/members/{member_user.id}/transfer/",
        {"target_organizational_unit_id": str(unrelated_region.id)},
        format="json",
    )
    assert response.status_code == 403


def test_ordinary_member_cannot_transfer_self(auth_client, member_user, national_unit):
    response = auth_client.post(
        f"/api/v1/auth/members/{member_user.id}/transfer/",
        {"target_organizational_unit_id": str(national_unit.id)},
        format="json",
    )
    assert response.status_code == 403
