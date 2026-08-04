import base64

import pytest

pytestmark = pytest.mark.django_db


def test_my_card_requires_authentication(api_client):
    response = api_client.get("/api/v1/membership/card/")
    assert response.status_code == 401


def test_my_card_returns_qr_code(auth_client, member_user):
    response = auth_client.get("/api/v1/membership/card/")
    assert response.status_code == 200
    body = response.json()
    assert body["membership_id"] == member_user.membership_id
    assert body["full_name"] == member_user.full_name
    # Confirm it's real, decodable PNG bytes, not a placeholder string.
    png_bytes = base64.b64decode(body["qr_code_base64"])
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_card_is_stable_across_requests(auth_client):
    first = auth_client.get("/api/v1/membership/card/").json()
    second = auth_client.get("/api/v1/membership/card/").json()
    assert first["qr_code_base64"] == second["qr_code_base64"]


def test_reissue_rotates_the_token(auth_client):
    from apps.membership.documents import MembershipCard

    first = auth_client.get("/api/v1/membership/card/").json()
    reissued = auth_client.post("/api/v1/membership/card/reissue/").json()
    assert first["qr_code_base64"] != reissued["qr_code_base64"]
    assert MembershipCard.objects.count() == 1  # rotated in place, not duplicated


def test_verify_valid_card(auth_client, member_user):
    from apps.membership.services import get_or_create_card

    card = get_or_create_card(member_user)
    response = auth_client.post(
        "/api/v1/membership/verify/", {"token": card.token}, format="json"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["membership_id"] == member_user.membership_id


def test_verify_accepts_full_qr_payload_prefix(auth_client, member_user):
    from apps.membership.services import QR_PREFIX, get_or_create_card

    card = get_or_create_card(member_user)
    response = auth_client.post(
        "/api/v1/membership/verify/",
        {"token": f"{QR_PREFIX}{card.token}"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_verify_rejects_bogus_token(auth_client):
    response = auth_client.post(
        "/api/v1/membership/verify/", {"token": "not-a-real-token"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_verify_rejects_revoked_token_after_reissue(auth_client):
    from apps.membership.documents import MembershipCard

    auth_client.get("/api/v1/membership/card/")
    auth_client.post("/api/v1/membership/card/reissue/")

    card = MembershipCard.objects.first()
    response = auth_client.post(
        "/api/v1/membership/verify/", {"token": "stale-token-value"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert card.token != "stale-token-value"
