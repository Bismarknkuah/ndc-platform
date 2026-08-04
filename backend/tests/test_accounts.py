import pytest

pytestmark = pytest.mark.django_db


def test_register_creates_user_and_returns_tokens(api_client, branch_unit):
    payload = {
        "email": "newmember@example.com",
        "phone_number": "0244000099",
        "password": "StrongPass123!",
        "first_name": "Yaw",
        "last_name": "Asare",
        "organizational_unit_id": str(branch_unit.id),
    }
    response = api_client.post("/api/v1/auth/register/", payload, format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "newmember@example.com"
    assert body["user"]["membership_id"].startswith("NDC-")
    assert "access" in body["tokens"] and "refresh" in body["tokens"]


def test_register_rejects_duplicate_email(api_client, branch_unit, member_user):
    payload = {
        "email": member_user.email,
        "phone_number": "0244000098",
        "password": "StrongPass123!",
        "first_name": "Yaw",
        "last_name": "Asare",
        "organizational_unit_id": str(branch_unit.id),
    }
    response = api_client.post("/api/v1/auth/register/", payload, format="json")
    assert response.status_code == 400
    assert "email" in response.json()["error"]["message"]


def test_login_success(api_client, member_user):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": member_user.email, "password": "StrongPass123!"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == member_user.email


def test_login_wrong_password_rejected(api_client, member_user):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": member_user.email, "password": "WrongPassword!"},
        format="json",
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_me_requires_authentication(api_client):
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == 401


def test_me_returns_profile_for_authenticated_user(auth_client, member_user):
    response = auth_client.get("/api/v1/auth/me/")
    assert response.status_code == 200
    assert response.json()["email"] == member_user.email


def test_can_upload_and_retrieve_own_profile_photo(auth_client, member_user):
    fake_photo = "aGVsbG8=" * 10  # small fake base64 payload, well under the cap
    response = auth_client.patch(
        "/api/v1/auth/me/",
        {"photo_base64": fake_photo, "photo_content_type": "image/png"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["photo_base64"] == fake_photo
    assert response.json()["has_photo"] is True

    # And it's actually persisted, not just echoed back.
    fetched = auth_client.get("/api/v1/auth/me/")
    assert fetched.json()["photo_base64"] == fake_photo


def test_oversized_photo_is_rejected(auth_client, member_user):
    too_large = "a" * 2_900_000
    response = auth_client.patch(
        "/api/v1/auth/me/", {"photo_base64": too_large}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_input"


def test_empty_photo_value_clears_existing_photo(auth_client, member_user):
    auth_client.patch("/api/v1/auth/me/", {"photo_base64": "aGVsbG8="}, format="json")
    response = auth_client.patch(
        "/api/v1/auth/me/", {"photo_base64": ""}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["has_photo"] is False
    assert response.json()["photo_base64"] in (None, "")


def test_member_list_strips_photo_base64_but_keeps_has_photo(
    chairman_client, member_user, auth_client
):
    auth_client.patch("/api/v1/auth/me/", {"photo_base64": "aGVsbG8="}, format="json")
    response = chairman_client.get("/api/v1/auth/members/list/")
    assert response.status_code == 200
    member_entry = next(
        m for m in response.json()["results"] if m["email"] == member_user.email
    )
    assert "photo_base64" not in member_entry
    assert member_entry["has_photo"] is True


def test_refresh_token_rotates_and_old_one_is_revoked(api_client, member_user):
    login = api_client.post(
        "/api/v1/auth/login/",
        {"email": member_user.email, "password": "StrongPass123!"},
        format="json",
    ).json()
    refresh_token = login["tokens"]["refresh"]

    first_refresh = api_client.post(
        "/api/v1/auth/refresh/", {"refresh": refresh_token}, format="json"
    )
    assert first_refresh.status_code == 200

    second_attempt_with_same_token = api_client.post(
        "/api/v1/auth/refresh/", {"refresh": refresh_token}, format="json"
    )
    assert second_attempt_with_same_token.status_code == 401


def test_logout_revokes_refresh_token(auth_client, member_user, api_client):
    login = api_client.post(
        "/api/v1/auth/login/",
        {"email": member_user.email, "password": "StrongPass123!"},
        format="json",
    ).json()
    refresh_token = login["tokens"]["refresh"]

    logout_response = auth_client.post(
        "/api/v1/auth/logout/", {"refresh": refresh_token}, format="json"
    )
    assert logout_response.status_code == 204

    refresh_attempt = api_client.post(
        "/api/v1/auth/refresh/", {"refresh": refresh_token}, format="json"
    )
    assert refresh_attempt.status_code == 401


def test_ordinary_member_cannot_assign_roles(
    auth_client, member_user, national_chairman_role
):
    response = auth_client.post(
        "/api/v1/auth/assign-role/",
        {"user_id": str(member_user.id), "role_id": str(national_chairman_role.id)},
        format="json",
    )
    assert response.status_code == 403


def test_national_chairman_can_assign_roles(
    chairman_client, member_user, national_chairman_role
):
    response = chairman_client.post(
        "/api/v1/auth/assign-role/",
        {"user_id": str(member_user.id), "role_id": str(national_chairman_role.id)},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["role"]["code"] == "national_chairman"


def test_invalid_bearer_token_is_rejected(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == 401
