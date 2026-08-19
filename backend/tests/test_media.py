import base64

import pytest

pytestmark = pytest.mark.django_db

_FAKE_PHOTO = base64.b64encode(b"fake-photo-bytes").decode("ascii")


def test_authorized_officer_can_upload_photo(chairman_client, national_unit):
    response = chairman_client.post(
        "/api/v1/media/",
        {
            "title": "Rally Photo",
            "media_type": "PHOTO",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_PHOTO,
            "is_public_within_party": True,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["file_base64"] == _FAKE_PHOTO


def test_can_reference_large_media_via_external_url(chairman_client, national_unit):
    response = chairman_client.post(
        "/api/v1/media/",
        {
            "title": "Rally Video",
            "media_type": "VIDEO",
            "organizational_unit_id": str(national_unit.id),
            "external_url": "https://youtube.com/watch?v=abc123",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["external_url"] == "https://youtube.com/watch?v=abc123"


def test_requires_either_file_or_url(chairman_client, national_unit):
    response = chairman_client.post(
        "/api/v1/media/",
        {
            "title": "Nothing attached",
            "media_type": "PHOTO",
            "organizational_unit_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 400


def test_ordinary_member_cannot_upload_media(auth_client, national_unit):
    response = auth_client.post(
        "/api/v1/media/",
        {
            "title": "Should fail",
            "media_type": "PHOTO",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_PHOTO,
        },
        format="json",
    )
    assert response.status_code == 403


def test_oversized_file_rejected(chairman_client, national_unit):
    response = chairman_client.post(
        "/api/v1/media/",
        {
            "title": "Huge",
            "media_type": "PHOTO",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": "A" * 8_000_000,
        },
        format="json",
    )
    assert response.status_code == 400


def test_public_media_visible_to_any_member(
    chairman_client, auth_client, national_unit
):
    chairman_client.post(
        "/api/v1/media/",
        {
            "title": "Public Photo",
            "media_type": "PHOTO",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_PHOTO,
            "is_public_within_party": True,
        },
        format="json",
    )
    response = auth_client.get("/api/v1/media/")
    titles = [m["title"] for m in response.json()["results"]]
    assert "Public Photo" in titles


def test_list_view_omits_file_payload(chairman_client, national_unit):
    chairman_client.post(
        "/api/v1/media/",
        {
            "title": "Photo",
            "media_type": "PHOTO",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_PHOTO,
            "is_public_within_party": True,
        },
        format="json",
    )
    response = chairman_client.get("/api/v1/media/")
    assert "file_base64" not in response.json()["results"][0]


def test_media_can_be_tagged_and_filtered(chairman_client, national_unit):
    chairman_client.post(
        "/api/v1/media/",
        {
            "title": "Tagged Photo",
            "media_type": "PHOTO",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_PHOTO,
            "tags": ["rally", "2028"],
            "is_public_within_party": True,
        },
        format="json",
    )
    response = chairman_client.get("/api/v1/media/?tag=rally")
    assert response.json()["count"] == 1


def test_media_can_be_linked_to_event(chairman_client, national_unit):
    import datetime

    start = datetime.datetime.utcnow().isoformat() + "Z"
    end = (datetime.datetime.utcnow() + datetime.timedelta(hours=2)).isoformat() + "Z"
    event = chairman_client.post(
        "/api/v1/events/",
        {
            "title": "Rally",
            "event_type": "RALLY",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()
    response = chairman_client.post(
        "/api/v1/media/",
        {
            "title": "Rally Photo",
            "media_type": "PHOTO",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_PHOTO,
            "event_id": event["id"],
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["event"]["id"] == event["id"]


def test_authority_can_delete_media(chairman_client, national_unit):
    created = chairman_client.post(
        "/api/v1/media/",
        {
            "title": "Photo",
            "media_type": "PHOTO",
            "organizational_unit_id": str(national_unit.id),
            "file_base64": _FAKE_PHOTO,
        },
        format="json",
    ).json()
    response = chairman_client.delete(f"/api/v1/media/{created['id']}/")
    assert response.status_code == 204

    follow_up = chairman_client.get(f"/api/v1/media/{created['id']}/")
    assert follow_up.status_code == 404
