import pytest

pytestmark = pytest.mark.django_db


def test_membership_analytics_requires_authority(auth_client, national_unit):
    response = auth_client.get(
        f"/api/v1/analytics/membership/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 403


def test_membership_analytics_counts_members(
    chairman_client, national_unit, member_user
):
    response = chairman_client.get(
        f"/api/v1/analytics/membership/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_members"] >= 1
    assert "gender_breakdown" in body
    assert len(body["growth_last_12_months"]) == 12


def test_membership_analytics_requires_unit_param(chairman_client):
    response = chairman_client.get("/api/v1/analytics/membership/")
    assert response.status_code == 400


def test_department_analytics_reports_task_breakdown(
    national_comms_director_client,
    communications_department,
    national_unit,
    national_chairman_user,
):
    import datetime

    national_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(national_chairman_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(national_unit.id),
            "position": "MEMBER",
        },
        format="json",
    )
    national_comms_director_client.post(
        "/api/v1/departments/tasks/",
        {
            "department_id": str(communications_department.id),
            "assigned_to_id": str(national_chairman_user.id),
            "title": "Radio interview",
            "engagement_type": "RADIO",
            "scheduled_at": (
                datetime.datetime.utcnow() + datetime.timedelta(days=1)
            ).isoformat()
            + "Z",
        },
        format="json",
    )

    response = national_comms_director_client.get(
        f"/api/v1/analytics/departments/?department_id={communications_department.id}"
        f"&organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_tasks"] == 1
    assert body["status_breakdown"]["PENDING"] == 1
    assert body["team_size"] == 2


def test_department_analytics_requires_both_params(
    chairman_client, communications_department
):
    response = chairman_client.get(
        f"/api/v1/analytics/departments/?department_id={communications_department.id}"
    )
    assert response.status_code == 400


def test_gis_map_returns_only_units_with_coordinates(
    chairman_client, national_unit, regional_unit
):
    response = chairman_client.get(
        f"/api/v1/analytics/map/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200
    assert response.json()["features"] == []


def test_gis_map_includes_units_with_coordinates_set(
    chairman_client, national_unit, regional_unit
):
    set_coords = chairman_client.patch(
        f"/api/v1/hierarchy/units/{regional_unit.id}/",
        {"latitude": 6.6885, "longitude": -1.6244},
        format="json",
    )
    assert set_coords.status_code == 200

    response = chairman_client.get(
        f"/api/v1/analytics/map/?organizational_unit_id={national_unit.id}"
    )
    features = response.json()["features"]
    assert len(features) == 1
    assert features[0]["geometry"]["coordinates"] == [-1.6244, 6.6885]
    assert features[0]["properties"]["name"] == regional_unit.name


def test_gis_map_filters_by_unit_type(
    chairman_client, national_unit, regional_unit, constituency_unit
):
    chairman_client.patch(
        f"/api/v1/hierarchy/units/{regional_unit.id}/",
        {"latitude": 6.0, "longitude": -1.0},
        format="json",
    )
    chairman_client.patch(
        f"/api/v1/hierarchy/units/{constituency_unit.id}/",
        {"latitude": 6.5, "longitude": -1.5},
        format="json",
    )

    response = chairman_client.get(
        f"/api/v1/analytics/map/?organizational_unit_id={national_unit.id}&unit_type=REGIONAL"
    )
    features = response.json()["features"]
    assert len(features) == 1
    assert features[0]["properties"]["unit_type"] == "REGIONAL"


def test_latitude_and_longitude_must_be_set_together(chairman_client, regional_unit):
    response = chairman_client.patch(
        f"/api/v1/hierarchy/units/{regional_unit.id}/",
        {"latitude": 6.0},
        format="json",
    )
    assert response.status_code == 400
