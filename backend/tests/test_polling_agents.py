import datetime

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def election(election_it_director_client, national_unit):
    start = datetime.datetime.utcnow().isoformat() + "Z"
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + "Z"
    return election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 General Election",
            "election_type": "NATIONAL_GENERAL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()


def test_authority_can_assign_polling_agent(
    election_it_director_client, election, branch_unit, member_user
):
    response = election_it_director_client.post(
        "/api/v1/elections/agents/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "agent_id": str(member_user.id),
            "role": "PARTY_AGENT",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["role"] == "PARTY_AGENT"
    assert response.json()["checked_in_at"] is None


def test_ordinary_member_cannot_assign_polling_agent(
    auth_client, election, branch_unit, member_user
):
    response = auth_client.post(
        "/api/v1/elections/agents/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "agent_id": str(member_user.id),
            "role": "PARTY_AGENT",
        },
        format="json",
    )
    assert response.status_code == 403


def test_cannot_double_assign_same_agent_to_same_branch(
    election_it_director_client, election, branch_unit, member_user
):
    payload = {
        "election_id": election["id"],
        "branch_unit_id": str(branch_unit.id),
        "agent_id": str(member_user.id),
        "role": "PARTY_AGENT",
    }
    first = election_it_director_client.post(
        "/api/v1/elections/agents/", payload, format="json"
    )
    assert first.status_code == 201
    second = election_it_director_client.post(
        "/api/v1/elections/agents/", payload, format="json"
    )
    assert second.status_code == 409


def test_agent_can_check_in(
    election_it_director_client, auth_client, election, branch_unit, member_user
):
    created = election_it_director_client.post(
        "/api/v1/elections/agents/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "agent_id": str(member_user.id),
            "role": "PARTY_AGENT",
        },
        format="json",
    ).json()

    response = auth_client.post(
        f"/api/v1/elections/agents/{created['id']}/check-in/",
        {"materials_confirmed": True},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["checked_in_at"] is not None
    assert response.json()["materials_confirmed"] is True


def test_unrelated_user_cannot_check_in_someone_elses_assignment(
    election_it_director_client, chairman_client, election, branch_unit, member_user
):
    created = election_it_director_client.post(
        "/api/v1/elections/agents/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "agent_id": str(member_user.id),
            "role": "PARTY_AGENT",
        },
        format="json",
    ).json()

    response = chairman_client.post(
        f"/api/v1/elections/agents/{created['id']}/check-in/"
    )
    assert response.status_code == 403


def test_agent_assignments_can_be_listed_by_election(
    election_it_director_client, election, branch_unit, member_user
):
    election_it_director_client.post(
        "/api/v1/elections/agents/",
        {
            "election_id": election["id"],
            "branch_unit_id": str(branch_unit.id),
            "agent_id": str(member_user.id),
            "role": "OBSERVER",
        },
        format="json",
    )
    response = election_it_director_client.get(
        f"/api/v1/elections/agents/?election_id={election['id']}"
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
