import datetime

import pytest

pytestmark = pytest.mark.django_db


def _future_window():
    start = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    end = start + datetime.timedelta(hours=1)
    return start.isoformat() + "Z", end.isoformat() + "Z"


@pytest.fixture
def completed_meeting(chairman_client, national_unit):
    start, end = _future_window()
    created = chairman_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Party Congress",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()
    chairman_client.patch(
        f"/api/v1/messaging/meetings/{created['id']}/",
        {"status": "COMPLETED"},
        format="json",
    )
    return created


def test_host_can_record_minutes(chairman_client, completed_meeting):
    response = chairman_client.post(
        f"/api/v1/messaging/meetings/{completed_meeting['id']}/minutes/",
        {
            "summary": "Discussed election readiness.",
            "decisions": "Approved regional budget increase.",
            "action_items": [
                {"description": "Follow up with regions", "is_done": False}
            ],
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["summary"] == "Discussed election readiness."
    assert len(response.json()["action_items"]) == 1


def test_non_host_cannot_record_minutes(auth_client, completed_meeting):
    response = auth_client.post(
        f"/api/v1/messaging/meetings/{completed_meeting['id']}/minutes/",
        {"summary": "Sneaky minutes."},
        format="json",
    )
    assert response.status_code == 403


def test_second_post_amends_existing_minutes(chairman_client, completed_meeting):
    chairman_client.post(
        f"/api/v1/messaging/meetings/{completed_meeting['id']}/minutes/",
        {"summary": "First draft."},
        format="json",
    )
    response = chairman_client.post(
        f"/api/v1/messaging/meetings/{completed_meeting['id']}/minutes/",
        {"summary": "Final version."},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["summary"] == "Final version."


def test_invitee_can_view_minutes(chairman_client, auth_client, completed_meeting):
    chairman_client.post(
        f"/api/v1/messaging/meetings/{completed_meeting['id']}/minutes/",
        {"summary": "Visible to invitees."},
        format="json",
    )
    response = auth_client.get(
        f"/api/v1/messaging/meetings/{completed_meeting['id']}/minutes/"
    )
    assert response.status_code == 200
    assert response.json()["summary"] == "Visible to invitees."


def test_minutes_default_attendees_from_rsvp(
    chairman_client, auth_client, completed_meeting, member_user
):
    auth_client.post(
        f"/api/v1/messaging/meetings/{completed_meeting['id']}/rsvp/",
        {"status": "ATTENDING"},
        format="json",
    )
    response = chairman_client.post(
        f"/api/v1/messaging/meetings/{completed_meeting['id']}/minutes/",
        {"summary": "Auto attendee test."},
        format="json",
    )
    attendee_ids = [a["id"] for a in response.json()["attendees"]]
    assert str(member_user.id) in attendee_ids


def test_action_item_can_be_assigned_to_a_user(
    chairman_client, completed_meeting, national_chairman_user
):
    response = chairman_client.post(
        f"/api/v1/messaging/meetings/{completed_meeting['id']}/minutes/",
        {
            "summary": "Assigning tasks.",
            "action_items": [
                {
                    "description": "Prepare regional report",
                    "assigned_to_id": str(national_chairman_user.id),
                }
            ],
        },
        format="json",
    )
    assert response.json()["action_items"][0]["assigned_to"]["id"] == str(
        national_chairman_user.id
    )


def test_no_minutes_yet_returns_404(chairman_client, completed_meeting):
    response = chairman_client.get(
        f"/api/v1/messaging/meetings/{completed_meeting['id']}/minutes/"
    )
    assert response.status_code == 404
