import pytest

pytestmark = pytest.mark.django_db


def test_ordinary_member_cannot_create_units(auth_client, national_unit):
    response = auth_client.post(
        "/api/v1/hierarchy/units/",
        {
            "name": "Ashanti Region",
            "code": "ndc-ashanti-2",
            "unit_type": "REGIONAL",
            "parent_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 403


def test_national_chairman_can_create_regional_unit(chairman_client, national_unit):
    response = chairman_client.post(
        "/api/v1/hierarchy/units/",
        {
            "name": "Ashanti Region",
            "code": "ndc-ashanti-3",
            "unit_type": "REGIONAL",
            "parent_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["unit_type"] == "REGIONAL"
    assert response.json()["parent_id"] == str(national_unit.id)


def test_regional_unit_rejects_wrong_parent_type(chairman_client, national_unit):
    # A CONSTITUENCY's parent must be REGIONAL, not NATIONAL.
    response = chairman_client.post(
        "/api/v1/hierarchy/units/",
        {
            "name": "Bad Constituency",
            "code": "ndc-bad-const",
            "unit_type": "CONSTITUENCY",
            "parent_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 400
    assert "parent_id" in response.json()["error"]["message"]


def test_national_unit_requires_no_parent(chairman_client):
    response = chairman_client.post(
        "/api/v1/hierarchy/units/",
        {
            "name": "Some National Body",
            "code": "ndc-some-national",
            "unit_type": "NATIONAL",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["parent_id"] is None


def test_auxiliary_wing_can_attach_under_regional_unit(chairman_client, regional_unit):
    response = chairman_client.post(
        "/api/v1/hierarchy/units/",
        {
            "name": "Ashanti Regional Women's Wing",
            "code": "ndc-ashanti-womens-wing",
            "unit_type": "WOMENS_WING",
            "parent_id": str(regional_unit.id),
        },
        format="json",
    )
    assert response.status_code == 201


def test_descendants_endpoint_returns_full_subtree(
    auth_client, national_unit, branch_unit
):
    response = auth_client.get(
        f"/api/v1/hierarchy/units/{national_unit.id}/descendants/"
    )
    assert response.status_code == 200
    names = {unit["name"] for unit in response.json()}
    assert branch_unit.name in names
    assert "Kumasi Central" in names


def test_ancestors_endpoint_returns_breadcrumb_to_root(
    auth_client, national_unit, branch_unit
):
    response = auth_client.get(f"/api/v1/hierarchy/units/{branch_unit.id}/ancestors/")
    assert response.status_code == 200
    ancestor_names = [unit["name"] for unit in response.json()]
    assert ancestor_names[-1] == national_unit.name


def test_cannot_deactivate_unit_with_active_children(
    chairman_client, national_unit, regional_unit
):
    response = chairman_client.delete(f"/api/v1/hierarchy/units/{national_unit.id}/")
    assert response.status_code == 409


def test_deactivate_leaf_unit_succeeds(chairman_client, branch_unit):
    response = chairman_client.delete(f"/api/v1/hierarchy/units/{branch_unit.id}/")
    assert response.status_code == 204


def test_list_units_filters_by_unit_type(auth_client, national_unit, regional_unit):
    response = auth_client.get("/api/v1/hierarchy/units/?unit_type=REGIONAL")
    assert response.status_code == 200
    results = response.json()["results"]
    assert all(unit["unit_type"] == "REGIONAL" for unit in results)
    assert any(unit["name"] == regional_unit.name for unit in results)
