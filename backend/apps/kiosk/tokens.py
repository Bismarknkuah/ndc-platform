"""
A kiosk vote token is deliberately not a normal login. It is issued only
after a real PIN check succeeds, carries the bare minimum (who, which
election, which kiosk), expires in minutes rather than the usual login
window, and is revoked (single-use) the instant a vote is actually cast.
Reuses the exact same signing mechanism and secret as normal account
tokens (apps.accounts.authentication._encode) but with type="kiosk_vote",
which the standard JWTAuthentication class already rejects outright for
every other endpoint in the platform - a kiosk token can never be used to
read a profile, send a message, or touch anything except the one ballot
it was issued for.
"""

from django.conf import settings

from apps.accounts.authentication import TokenError, _encode, decode_token, revoke_token


def issue_kiosk_vote_token(user, election, kiosk) -> str:
    return _encode(
        {
            "sub": str(user.id),
            "election_id": str(election.id),
            "kiosk_id": str(kiosk.id),
            "type": "kiosk_vote",
        },
        settings.JWT_KIOSK_VOTE_TOKEN_TTL,
    )


def decode_kiosk_vote_token(token: str) -> dict:
    return decode_token(token, expected_type="kiosk_vote")


def revoke_kiosk_vote_token(token: str):
    revoke_token(token, expected_type="kiosk_vote")


__all__ = [
    "issue_kiosk_vote_token",
    "decode_kiosk_vote_token",
    "revoke_kiosk_vote_token",
    "TokenError",
]
