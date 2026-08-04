import datetime
import uuid

import jwt
from django.conf import settings
from django.core.cache import cache
from mongoengine.errors import DoesNotExist, ValidationError
from rest_framework import authentication

from apps.accounts.documents import User


class TokenError(Exception):
    pass


def _blacklist_key(jti: str) -> str:
    return f"jwt:blacklist:{jti}"


def _encode(payload: dict, ttl: datetime.timedelta) -> str:
    now = datetime.datetime.utcnow()
    full_payload = {**payload, "iat": now, "exp": now + ttl, "jti": str(uuid.uuid4())}
    return jwt.encode(
        full_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )


def issue_token_pair(user: User) -> dict:
    """Issues an access + refresh JWT pair for a successfully authenticated user."""
    base_claims = {
        "sub": str(user.id),
        "email": user.email,
        "role_code": user.role.code if user.role else None,
        "unit_id": (
            str(user.organizational_unit.id) if user.organizational_unit else None
        ),
    }
    access_token = _encode(
        {**base_claims, "type": "access"}, settings.JWT_ACCESS_TOKEN_TTL
    )
    refresh_token = _encode(
        {**base_claims, "type": "refresh"}, settings.JWT_REFRESH_TOKEN_TTL
    )
    return {
        "access": access_token,
        "refresh": refresh_token,
        "access_expires_in": int(settings.JWT_ACCESS_TOKEN_TTL.total_seconds()),
    }


def decode_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token is invalid.") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"Expected a {expected_type} token.")

    if cache.get(_blacklist_key(payload.get("jti", ""))):
        raise TokenError("Token has been revoked.")

    return payload


def revoke_token(token: str, expected_type: str = "refresh"):
    """Blacklists a token's jti in Redis for the remainder of its natural life."""
    payload = decode_token(token, expected_type=expected_type)
    exp = datetime.datetime.utcfromtimestamp(payload["exp"])
    ttl_seconds = max(int((exp - datetime.datetime.utcnow()).total_seconds()), 1)
    cache.set(_blacklist_key(payload["jti"]), True, timeout=ttl_seconds)


def refresh_access_token(refresh_token: str) -> dict:
    payload = decode_token(refresh_token, expected_type="refresh")
    try:
        user = User.objects.get(id=payload["sub"], is_active=True)
    except (DoesNotExist, ValidationError) as exc:
        raise TokenError("User no longer exists or is inactive.") from exc
    # Rotate: the old refresh token is single-use.
    revoke_token(refresh_token, expected_type="refresh")
    return issue_token_pair(user)


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Stateless JWT authentication reading `Authorization: Bearer <token>`.
    Populates request.user with a MongoEngine User document (or
    AnonymousUser when no/invalid credentials are supplied).
    """

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None  # no credentials supplied -> other auth classes / AnonymousUser via DRF default

        token = header[len(self.keyword) + 1 :]
        try:
            payload = decode_token(token, expected_type="access")
        except TokenError as exc:
            from rest_framework.exceptions import AuthenticationFailed

            raise AuthenticationFailed(str(exc)) from exc

        try:
            user = User.objects.get(id=payload["sub"], is_active=True)
        except (DoesNotExist, ValidationError) as exc:
            from rest_framework.exceptions import AuthenticationFailed

            raise AuthenticationFailed("User no longer exists or is inactive.") from exc

        return (user, token)

    def authenticate_header(self, request):
        return self.keyword
