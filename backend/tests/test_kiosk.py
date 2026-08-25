import datetime

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _window():
    start = datetime.datetime.utcnow().isoformat() + "Z"
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + "Z"
    return start, end


def _open_election_with_candidate(election_it_director_client, national_unit):
    start, end = _window()
    election = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "2028 Presidential Primary",
            "election_type": "PRESIDENTIAL_PRIMARY",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()
    candidate = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/candidates/",
        {"name": "Kiosk Test Candidate"},
        format="json",
    ).json()
    election_it_director_client.patch(
        f"/api/v1/elections/{election['id']}/", {"status": "OPEN"}, format="json"
    )
    return election, candidate


def _register_kiosk(election_it_director_client, election, national_unit):
    response = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/kiosks/",
        {"unit_id": str(national_unit.id), "label": "Test Polling Terminal"},
        format="json",
    )
    return response.json()


def test_member_can_set_and_use_a_kiosk_pin(member_user):
    """The whole security foundation: a member sets their own PIN through
    their real authenticated account, requiring their real password -
    never settable by anyone else."""
    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(member_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.post(
        "/api/v1/kiosk/my-pin/",
        {"current_password": "StrongPass123!", "pin": "1234"},
        format="json",
    )
    assert response.status_code == 204

    member_user.reload()
    assert member_user.check_kiosk_pin("1234") is True
    assert member_user.check_kiosk_pin("9999") is False


def test_cannot_set_pin_without_the_real_account_password(member_user):
    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(member_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.post(
        "/api/v1/kiosk/my-pin/",
        {"current_password": "WrongPassword!", "pin": "1234"},
        format="json",
    )
    assert response.status_code == 400
    member_user.reload()
    assert member_user.kiosk_pin_hash is None


def test_pin_must_be_4_to_6_digits(member_user):
    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(member_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.post(
        "/api/v1/kiosk/my-pin/",
        {"current_password": "StrongPass123!", "pin": "12"},
        format="json",
    )
    assert response.status_code == 400


def test_only_election_it_director_can_register_a_kiosk(
    chairman_client, election_it_director_client, national_unit
):
    """Registering a kiosk is part of organizing the election - not even
    the Chairman can do it, matching centralized election authority."""
    election, _ = _open_election_with_candidate(
        election_it_director_client, national_unit
    )

    forbidden = chairman_client.post(
        f"/api/v1/elections/{election['id']}/kiosks/",
        {"unit_id": str(national_unit.id), "label": "Should Fail"},
        format="json",
    )
    assert forbidden.status_code == 403

    allowed = election_it_director_client.post(
        f"/api/v1/elections/{election['id']}/kiosks/",
        {"unit_id": str(national_unit.id), "label": "Should Succeed"},
        format="json",
    )
    assert allowed.status_code == 201
    assert "kiosk_code" in allowed.json()


def test_kiosk_code_is_never_shown_again_after_creation(
    election_it_director_client, national_unit
):
    election, _ = _open_election_with_candidate(
        election_it_director_client, national_unit
    )
    kiosk = _register_kiosk(election_it_director_client, election, national_unit)

    response = election_it_director_client.get(
        f"/api/v1/elections/{election['id']}/kiosks/"
    )
    assert response.status_code == 200
    for entry in response.json():
        assert "kiosk_code" not in entry
    assert "kiosk_code" in kiosk  # confirmed shown once, at creation


def test_full_kiosk_voting_flow_end_to_end(
    election_it_director_client, national_unit, member_user
):
    """The real, complete walk-up flow: set a PIN, verify at a kiosk with
    membership ID + PIN (no login), get a narrow token, cast one vote."""
    election, candidate = _open_election_with_candidate(
        election_it_director_client, national_unit
    )
    kiosk = _register_kiosk(election_it_director_client, election, national_unit)

    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(member_user)
    member_client = APIClient()
    member_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    member_client.post(
        "/api/v1/kiosk/my-pin/",
        {"current_password": "StrongPass123!", "pin": "4321"},
        format="json",
    )

    kiosk_client = APIClient()  # no auth header at all - this is the point
    verify_response = kiosk_client.post(
        "/api/v1/kiosk/verify/",
        {
            "kiosk_code": kiosk["kiosk_code"],
            "membership_id": member_user.membership_id,
            "pin": "4321",
        },
        format="json",
    )
    assert verify_response.status_code == 200
    kiosk_vote_token = verify_response.json()["kiosk_vote_token"]

    vote_response = kiosk_client.post(
        "/api/v1/kiosk/vote/",
        {"kiosk_vote_token": kiosk_vote_token, "candidate_id": candidate["id"]},
        format="json",
    )
    assert vote_response.status_code == 201


def test_wrong_pin_is_rejected_with_a_generic_error(
    election_it_director_client, national_unit, member_user
):
    election, _ = _open_election_with_candidate(
        election_it_director_client, national_unit
    )
    kiosk = _register_kiosk(election_it_director_client, election, national_unit)

    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(member_user)
    member_client = APIClient()
    member_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    member_client.post(
        "/api/v1/kiosk/my-pin/",
        {"current_password": "StrongPass123!", "pin": "4321"},
        format="json",
    )

    response = APIClient().post(
        "/api/v1/kiosk/verify/",
        {
            "kiosk_code": kiosk["kiosk_code"],
            "membership_id": member_user.membership_id,
            "pin": "0000",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "kiosk_verification_failed"


def test_pin_locks_out_after_repeated_wrong_attempts(
    election_it_director_client, national_unit, member_user
):
    """The actual brute-force defense - a small PIN space (10,000
    combinations for 4 digits) is only safe with a real lockout."""
    election, _ = _open_election_with_candidate(
        election_it_director_client, national_unit
    )
    kiosk = _register_kiosk(election_it_director_client, election, national_unit)

    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(member_user)
    member_client = APIClient()
    member_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    member_client.post(
        "/api/v1/kiosk/my-pin/",
        {"current_password": "StrongPass123!", "pin": "4321"},
        format="json",
    )

    kiosk_client = APIClient()
    for _ in range(5):
        kiosk_client.post(
            "/api/v1/kiosk/verify/",
            {
                "kiosk_code": kiosk["kiosk_code"],
                "membership_id": member_user.membership_id,
                "pin": "0000",
            },
            format="json",
        )

    # Even the CORRECT pin is now rejected - locked out.
    response = kiosk_client.post(
        "/api/v1/kiosk/verify/",
        {
            "kiosk_code": kiosk["kiosk_code"],
            "membership_id": member_user.membership_id,
            "pin": "4321",
        },
        format="json",
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "kiosk_pin_locked"


def test_unknown_kiosk_code_is_rejected(member_user):
    """A fake/unregistered kiosk endpoint must never work, even with a
    completely correct membership ID and PIN - the terminal itself must
    be a real, registered device."""
    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(member_user)
    member_client = APIClient()
    member_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    member_client.post(
        "/api/v1/kiosk/my-pin/",
        {"current_password": "StrongPass123!", "pin": "4321"},
        format="json",
    )

    response = APIClient().post(
        "/api/v1/kiosk/verify/",
        {
            "kiosk_code": "KIOSK-FAKE0000",
            "membership_id": member_user.membership_id,
            "pin": "4321",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "kiosk_verification_failed"


def test_kiosk_vote_token_cannot_be_reused_for_a_second_vote(
    election_it_director_client, national_unit, member_user
):
    election, candidate = _open_election_with_candidate(
        election_it_director_client, national_unit
    )
    kiosk = _register_kiosk(election_it_director_client, election, national_unit)

    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(member_user)
    member_client = APIClient()
    member_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    member_client.post(
        "/api/v1/kiosk/my-pin/",
        {"current_password": "StrongPass123!", "pin": "4321"},
        format="json",
    )

    kiosk_client = APIClient()
    verify_response = kiosk_client.post(
        "/api/v1/kiosk/verify/",
        {
            "kiosk_code": kiosk["kiosk_code"],
            "membership_id": member_user.membership_id,
            "pin": "4321",
        },
        format="json",
    )
    token = verify_response.json()["kiosk_vote_token"]

    first = kiosk_client.post(
        "/api/v1/kiosk/vote/",
        {"kiosk_vote_token": token, "candidate_id": candidate["id"]},
        format="json",
    )
    assert first.status_code == 201

    second = kiosk_client.post(
        "/api/v1/kiosk/vote/",
        {"kiosk_vote_token": token, "candidate_id": candidate["id"]},
        format="json",
    )
    assert second.status_code == 401


def test_kiosk_vote_token_cannot_access_any_other_endpoint(
    election_it_director_client, national_unit, member_user
):
    """Confirms real isolation: a kiosk token is not a login - it must be
    rejected by every normal authenticated endpoint in the platform."""
    election, _ = _open_election_with_candidate(
        election_it_director_client, national_unit
    )
    kiosk = _register_kiosk(election_it_director_client, election, national_unit)

    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(member_user)
    member_client = APIClient()
    member_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    member_client.post(
        "/api/v1/kiosk/my-pin/",
        {"current_password": "StrongPass123!", "pin": "4321"},
        format="json",
    )

    kiosk_client = APIClient()
    verify_response = kiosk_client.post(
        "/api/v1/kiosk/verify/",
        {
            "kiosk_code": kiosk["kiosk_code"],
            "membership_id": member_user.membership_id,
            "pin": "4321",
        },
        format="json",
    )
    token = verify_response.json()["kiosk_vote_token"]

    hijack_attempt = APIClient()
    hijack_attempt.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = hijack_attempt.get("/api/v1/auth/me/")
    assert response.status_code == 401


def test_deactivated_kiosk_can_no_longer_be_used(
    election_it_director_client, national_unit, member_user
):
    election, _ = _open_election_with_candidate(
        election_it_director_client, national_unit
    )
    kiosk = _register_kiosk(election_it_director_client, election, national_unit)

    from apps.kiosk.documents import VotingKiosk

    VotingKiosk.objects(id=kiosk["id"]).update(is_active=False)

    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(member_user)
    member_client = APIClient()
    member_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    member_client.post(
        "/api/v1/kiosk/my-pin/",
        {"current_password": "StrongPass123!", "pin": "4321"},
        format="json",
    )

    response = APIClient().post(
        "/api/v1/kiosk/verify/",
        {
            "kiosk_code": kiosk["kiosk_code"],
            "membership_id": member_user.membership_id,
            "pin": "4321",
        },
        format="json",
    )
    assert response.status_code == 400


def test_member_with_no_pin_set_cannot_verify_at_a_kiosk(
    election_it_director_client, national_unit, member_user
):
    election, _ = _open_election_with_candidate(
        election_it_director_client, national_unit
    )
    kiosk = _register_kiosk(election_it_director_client, election, national_unit)

    response = APIClient().post(
        "/api/v1/kiosk/verify/",
        {
            "kiosk_code": kiosk["kiosk_code"],
            "membership_id": member_user.membership_id,
            "pin": "0000",
        },
        format="json",
    )
    assert response.status_code == 400
