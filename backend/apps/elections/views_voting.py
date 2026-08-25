from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import (
    DoesNotExist,
    NotUniqueError,
    ValidationError as MongoValidationError,
)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.documents import User
from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.elections.documents import Election, EligibleVoter, Vote
from apps.elections.permissions import can_manage_voters, is_eligible_voter
from apps.elections.serializers import (
    AddEligibleVotersSerializer,
    CastVoteSerializer,
    EligibleVoterSerializer,
    VoteReceiptSerializer,
)


def _get_election_or_404(election_id):
    try:
        return Election.objects.get(id=election_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Election not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class EligibleVoterListCreateView(APIView):
    """
    GET  /api/v1/elections/<id>/voters/   - list the selected electorate (director-only)
    POST /api/v1/elections/<id>/voters/   {"user_ids": [...]} - select who qualifies to
         vote. Each newly-added voter gets a notification ("those who
         qualify have to see notification and use their portal to vote").
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: EligibleVoterSerializer(many=True)}, tags=["elections"]
    )
    def get(self, request, election_id):
        election = _get_election_or_404(election_id)
        if not can_manage_voters(request.user, election):
            raise APIError(
                "You do not have authority to view this election's electorate.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        voters = EligibleVoter.objects(election=election)
        return Response(EligibleVoterSerializer(voters, many=True).data)

    @extend_schema(
        request=AddEligibleVotersSerializer,
        responses={201: EligibleVoterSerializer(many=True)},
        tags=["elections"],
    )
    def post(self, request, election_id):
        election = _get_election_or_404(election_id)
        from apps.elections.constants import MANDATORY_OPEN_ELECTORATE_TYPES

        if election.election_type in MANDATORY_OPEN_ELECTORATE_TYPES:
            raise APIError(
                "This election type is open to every active member by "
                "Supreme Court ruling - the electorate cannot be "
                "curated or restricted.",
                code="mandatory_open_electorate",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if not can_manage_voters(request.user, election):
            raise APIError(
                "You do not have authority to select this election's electorate.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AddEligibleVotersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.messaging.services import notify

        added = []
        for user_id in serializer.validated_data["user_ids"]:
            try:
                voter_user = User.objects.get(id=user_id, is_active=True)
            except (DoesNotExist, MongoValidationError):
                continue
            existing = EligibleVoter.objects(election=election, user=voter_user).first()
            if existing:
                added.append(existing)
                continue
            record = EligibleVoter.objects.create(
                election=election, user=voter_user, added_by=request.user
            )
            added.append(record)
            notify(
                voter_user,
                "ELECTION_ELIGIBILITY",
                title=f"You may vote in: {election.title}",
                body="You have been added to the electorate for this election. Cast your vote from your portal.",
                target=election,
            )

        log_action(
            request.user,
            "elections.voters.add",
            request=request,
            target=election,
            description=f"Added {len(added)} eligible voter(s) to {election.title}",
        )
        return Response(
            EligibleVoterSerializer(added, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class EligibleVoterDetailView(APIView):
    """DELETE /api/v1/elections/<id>/voters/<user_id>/ - revoke eligibility (director-only)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None}, tags=["elections"])
    def delete(self, request, election_id, user_id):
        election = _get_election_or_404(election_id)
        if not can_manage_voters(request.user, election):
            raise APIError(
                "You do not have authority to modify this election's electorate.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        EligibleVoter.objects(election=election, user=user_id).delete()
        log_action(
            request.user,
            "elections.voters.remove",
            request=request,
            target=election,
            description=user_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyEligibilityView(APIView):
    """GET /api/v1/elections/<id>/my-eligibility/ - a member checks their own voting status."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["elections"])
    def get(self, request, election_id):
        election = _get_election_or_404(election_id)
        eligible = is_eligible_voter(request.user, election)
        voted_positions = list(
            Vote.objects(election=election, voter=request.user).distinct("position")
        )
        return Response(
            {
                "eligible": eligible,
                "election_status": election.status,
                "voted_positions": voted_positions,
            }
        )


class CastVoteView(APIView):
    """
    POST /api/v1/elections/<id>/vote/  {"candidate_id": "...", "position": optional}
    An eligible voter casts their own ballot. One vote per (election,
    position) per voter, enforced at the database level; the election
    must be OPEN.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CastVoteSerializer,
        responses={201: VoteReceiptSerializer},
        tags=["elections"],
    )
    def post(self, request, election_id):
        election = _get_election_or_404(election_id)

        if not is_eligible_voter(request.user, election):
            raise APIError(
                "You are not on the electorate for this election.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if election.status != "OPEN":
            raise APIError(
                "This election is not currently open for voting.",
                code="election_not_open",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

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
            vote = Vote.objects.create(
                election=election,
                position=position,
                voter=request.user,
                candidate=candidate,
            )
        except NotUniqueError as exc:
            raise APIError(
                "You have already voted in this race.",
                code="already_voted",
                http_status=status.HTTP_409_CONFLICT,
            ) from exc

        log_action(
            request.user,
            "elections.vote.cast",
            request=request,
            target=election,
            description=f"position={position}",
        )
        return Response(
            VoteReceiptSerializer(vote).data, status=status.HTTP_201_CREATED
        )
