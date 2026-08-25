import datetime
import secrets

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import (
    DoesNotExist,
    NotUniqueError,
    ValidationError as MongoValidationError,
)
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.documents import User
from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.elections.documents import Election, Vote
from apps.elections.permissions import is_eligible_voter
from apps.elections.serializers import CastVoteSerializer
from apps.kiosk.documents import VotingKiosk
from apps.kiosk.permissions import can_register_kiosk
from apps.kiosk.serializers import (
    KioskCastVoteSerializer,
    KioskRegistrationSerializer,
    KioskVerifySerializer,
    SetKioskPinSerializer,
)
from apps.kiosk.tokens import (
    TokenError,
    decode_kiosk_vote_token,
    issue_kiosk_vote_token,
    revoke_kiosk_vote_token,
)

MAX_PIN_ATTEMPTS = 5
PIN_LOCKOUT = datetime.timedelta(minutes=15)


class SetKioskPinView(APIView):
    """
    POST /api/v1/kiosk/my-pin/  {"current_password": "...", "pin": "1234"}
    A member sets or changes their own Kiosk Voting PIN through their
    real, authenticated account - never settable by anyone else, and
    never settable without proving the real account password first, so
    knowing someone's membership ID is never enough on its own to give
    them a working kiosk credential.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(request=SetKioskPinSerializer, responses={204: None}, tags=["kiosk"])
    def post(self, request):
        serializer = SetKioskPinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            raise APIError(
                "Current password is incorrect.",
                code="invalid_credentials",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_kiosk_pin(serializer.validated_data["pin"])
        user.save()
        log_action(user, "kiosk.pin.set", request=request, target=user)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _get_election_or_404(election_id):
    try:
        return Election.objects.get(id=election_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Election not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class KioskRegistrationView(APIView):
    """
    POST /api/v1/elections/<election_id>/kiosks/
    The Election/IT Director registers a real, physical walk-up voting
    terminal for this election. Returns a `kiosk_code` shown exactly
    once - it identifies the device, it is not itself a secret (the
    security is the voter's own PIN), but it is still only shown at
    creation time, same as an API key, so it can't be silently re-read
    later by anyone who gains access to the record.

    GET does not include kiosk_code at all - only label/status, to
    confirm which physical terminals exist without re-exposing the code.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=KioskRegistrationSerializer,
        responses={201: KioskRegistrationSerializer},
        tags=["kiosk"],
    )
    def post(self, request, election_id):
        election = _get_election_or_404(election_id)
        if not can_register_kiosk(request.user, election):
            raise APIError(
                "You do not have authority to register a kiosk for this election.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        serializer = KioskRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kiosk_code = f"KIOSK-{secrets.token_hex(4).upper()}"
        kiosk = VotingKiosk.objects.create(
            election=election,
            unit=serializer.validated_data["unit_id"],
            label=serializer.validated_data["label"],
            kiosk_code=kiosk_code,
            created_by=request.user,
        )
        kiosk._show_kiosk_code = True
        log_action(request.user, "kiosk.register", request=request, target=election)
        return Response(
            KioskRegistrationSerializer(kiosk).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        responses={200: KioskRegistrationSerializer(many=True)}, tags=["kiosk"]
    )
    def get(self, request, election_id):
        election = _get_election_or_404(election_id)
        if not can_register_kiosk(request.user, election):
            raise APIError(
                "You do not have authority to view kiosks for this election.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        kiosks = VotingKiosk.objects(election=election)
        return Response(KioskRegistrationSerializer(kiosks, many=True).data)


class KioskVerifyView(APIView):
    """
    POST /api/v1/kiosk/verify/  {"kiosk_code": "...", "membership_id": "...", "pin": "..."}

    No account login involved - this is the walk-up-terminal step. On
    success, returns a kiosk_vote_token: a narrow, minutes-long,
    single-use token that can only be used to cast one ballot in the one
    election this kiosk is registered for - never a substitute for a
    real account login, and immediately rejected by every other endpoint
    in the platform (see apps.kiosk.tokens).

    Deliberately one generic error for every failure reason (unknown
    kiosk code, unknown membership ID, no PIN ever set, wrong PIN) - a
    kiosk terminal must never reveal which part was wrong, the same
    principle as a normal login not confirming whether an email exists.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=KioskVerifySerializer,
        responses={200: OpenApiTypes.OBJECT},
        tags=["kiosk"],
    )
    def post(self, request):
        serializer = KioskVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        generic_error = APIError(
            "Could not verify - check the kiosk code, membership ID, and PIN.",
            code="kiosk_verification_failed",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

        kiosk = VotingKiosk.objects(
            kiosk_code=data["kiosk_code"], is_active=True
        ).first()
        if kiosk is None:
            raise generic_error

        user = User.objects(membership_id=data["membership_id"], is_active=True).first()
        if user is None:
            raise generic_error

        if user.kiosk_pin_is_locked:
            raise APIError(
                "Too many incorrect attempts. Try again later or ask a "
                "polling official for help.",
                code="kiosk_pin_locked",
                http_status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not user.check_kiosk_pin(data["pin"]):
            user.kiosk_pin_failed_attempts += 1
            if user.kiosk_pin_failed_attempts >= MAX_PIN_ATTEMPTS:
                user.kiosk_pin_locked_until = datetime.datetime.utcnow() + PIN_LOCKOUT
            user.save()
            raise generic_error

        # Correct PIN - reset the failure counter.
        user.kiosk_pin_failed_attempts = 0
        user.kiosk_pin_locked_until = None
        user.save()

        if kiosk.election.status != "OPEN":
            raise APIError(
                "This election is not currently open for voting.",
                code="election_not_open",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        if not is_eligible_voter(user, kiosk.election):
            raise APIError(
                "You are not eligible to vote in this election.",
                code="not_eligible",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        token = issue_kiosk_vote_token(user, kiosk.election, kiosk)
        log_action(user, "kiosk.verify.success")
        return Response(
            {
                "kiosk_vote_token": token,
                "election_id": str(kiosk.election.id),
                "election_title": kiosk.election.title,
                "voter_name": user.full_name,
            }
        )


class KioskCastVoteView(APIView):
    """
    POST /api/v1/kiosk/vote/  {"kiosk_vote_token": "...", "candidate_id": "...", "position": optional}
    Casts a ballot using the narrow token from KioskVerifyView instead of
    a normal account login. The token is revoked (single-use) the moment
    this succeeds or fails with a real, final answer, so it can never be
    replayed to cast a second vote even within its short natural life.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=KioskCastVoteSerializer,
        responses={201: OpenApiTypes.OBJECT},
        tags=["kiosk"],
    )
    def post(self, request):
        raw_token = request.data.get("kiosk_vote_token")
        if not raw_token:
            raise APIError(
                "kiosk_vote_token is required.",
                code="missing_token",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = decode_kiosk_vote_token(raw_token)
        except TokenError as exc:
            raise APIError(
                "This kiosk session has expired or already been used - "
                "start again at the kiosk.",
                code="invalid_kiosk_token",
                http_status=status.HTTP_401_UNAUTHORIZED,
            ) from exc

        try:
            user = User.objects.get(id=payload["sub"], is_active=True)
            election = Election.objects.get(id=payload["election_id"])
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Voter or election no longer exists.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

        serializer = CastVoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidate = serializer.validated_data["candidate_id"]
        position = serializer.validated_data.get("position")

        if str(candidate.election.id) != str(election.id):
            raise APIError(
                "That candidate is not contesting this election.",
                code="invalid_candidate",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if candidate.position != position:
            raise APIError(
                "Candidate/position mismatch.",
                code="invalid_candidate",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            Vote.objects.create(
                election=election, position=position, voter=user, candidate=candidate
            )
        except NotUniqueError as exc:
            revoke_kiosk_vote_token(raw_token)
            raise APIError(
                "You have already voted in this race.",
                code="already_voted",
                http_status=status.HTTP_409_CONFLICT,
            ) from exc

        # Single-use, regardless of outcome from here - a kiosk token
        # never survives past its one real attempt.
        revoke_kiosk_vote_token(raw_token)

        log_action(
            user, "kiosk.vote.cast", target=election, description=f"position={position}"
        )
        return Response({"status": "recorded"}, status=status.HTTP_201_CREATED)
