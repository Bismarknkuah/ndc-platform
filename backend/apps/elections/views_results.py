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

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.elections.documents import CandidateTally, ResultSubmission
from apps.elections.permissions import (
    can_manage_election,
    can_submit_result,
    can_verify_result,
)
from apps.elections.serializers import ResultSubmissionSerializer
from apps.elections.services import aggregate_results, branches_in_scope
from apps.hierarchy.documents import OrganizationalUnit


def _get_submission_or_404(submission_id):
    try:
        return ResultSubmission.objects.get(id=submission_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Result submission not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class ResultSubmissionListCreateView(APIView):
    """
    GET  /api/v1/elections/results/?election_id=&branch_unit_id=&organizational_unit_id=&status=
         List result submissions ("collation sheets"). `branch_unit_id`
         matches one exact polling station; `organizational_unit_id`
         matches every branch in that unit's subtree (e.g. a Constituency
         or Regional IT director listing every result in their
         jurisdiction) and requires election-management authority over
         that unit.

    POST /api/v1/elections/results/
         A branch executive submits their branch's (polling station's)
         official result for one race. Exactly one submission per
         (election, branch, position) - resubmitting returns 409; use
         PATCH on the existing submission to amend it.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: ResultSubmissionSerializer(many=True)}, tags=["elections"]
    )
    def get(self, request):
        qs = ResultSubmission.objects.all()

        election_id = request.query_params.get("election_id")
        if election_id:
            qs = qs.filter(election=election_id)

        branch_unit_id = request.query_params.get("branch_unit_id")
        if branch_unit_id:
            qs = qs.filter(branch_unit=branch_unit_id)

        organizational_unit_id = request.query_params.get("organizational_unit_id")
        if organizational_unit_id:
            try:
                jurisdiction_unit = OrganizationalUnit.objects.get(
                    id=organizational_unit_id, is_active=True
                )
            except (DoesNotExist, MongoValidationError) as exc:
                raise APIError(
                    "Organizational unit not found.",
                    code="not_found",
                    http_status=status.HTTP_404_NOT_FOUND,
                ) from exc
            if not can_manage_election(request.user, jurisdiction_unit):
                raise APIError(
                    "You do not have authority to view results across this jurisdiction.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            branch_ids = [b.id for b in branches_in_scope(jurisdiction_unit)]
            qs = qs.filter(branch_unit__in=branch_ids)

        result_status = request.query_params.get("status")
        if result_status:
            qs = qs.filter(status=result_status)

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            ResultSubmissionSerializer(page, many=True).data
        )

    @extend_schema(
        request=ResultSubmissionSerializer,
        responses={201: ResultSubmissionSerializer},
        tags=["elections"],
    )
    def post(self, request):
        serializer = ResultSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        election = serializer.validated_data["election_id"]
        branch_unit = serializer.validated_data["branch_unit_id"]
        position = serializer.validated_data.get("position")

        if not can_submit_result(request.user, branch_unit):
            raise APIError(
                "Only an executive of this branch may submit its result.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        tallies = [
            CandidateTally(candidate=t["candidate_id"], votes=t["votes"])
            for t in serializer.validated_data["tallies"]
        ]

        try:
            submission = ResultSubmission.objects.create(
                election=election,
                branch_unit=branch_unit,
                position=position,
                submitted_by=request.user,
                tallies=tallies,
                collation_sheet_photo_base64=serializer.validated_data[
                    "collation_sheet_photo_base64"
                ],
                total_registered_voters=serializer.validated_data.get(
                    "total_registered_voters"
                ),
                total_valid_votes=serializer.validated_data.get("total_valid_votes"),
                total_rejected_votes=serializer.validated_data.get(
                    "total_rejected_votes"
                ),
            )
        except NotUniqueError as exc:
            raise APIError(
                "A result has already been submitted for this branch and race. Use PATCH to amend it.",
                code="conflict",
                http_status=status.HTTP_409_CONFLICT,
            ) from exc

        log_action(
            request.user,
            "elections.result.submit",
            request=request,
            target=submission,
            description=f"{election.title} @ {branch_unit.name}",
        )
        return Response(
            ResultSubmissionSerializer(submission).data, status=status.HTTP_201_CREATED
        )


class ResultSubmissionDetailView(APIView):
    """
    GET   /api/v1/elections/results/<id>/
    PATCH /api/v1/elections/results/<id>/  - the submitting branch executive
          can amend tallies/totals; collation authority (elections.manage
          over that branch or an ancestor of it) can VERIFY or DISPUTE.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ResultSubmissionSerializer}, tags=["elections"])
    def get(self, request, submission_id):
        submission = _get_submission_or_404(submission_id)
        return Response(ResultSubmissionSerializer(submission).data)

    @extend_schema(
        request=ResultSubmissionSerializer,
        responses={200: ResultSubmissionSerializer},
        tags=["elections"],
    )
    def patch(self, request, submission_id):
        submission = _get_submission_or_404(submission_id)
        is_submitter = submission.submitted_by.id == request.user.id
        has_authority = can_verify_result(request.user, submission.branch_unit)

        new_status = request.data.get("status")
        if new_status in ("VERIFIED", "DISPUTED"):
            if not has_authority:
                raise APIError(
                    "Only the collation authority for this branch can verify/dispute a result.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            if new_status == "VERIFIED":
                submission.mark_verified(request.user)
            else:
                submission.mark_disputed(request.user)

        if "tallies" in request.data:
            if not (is_submitter or has_authority):
                raise APIError(
                    "Only the submitting branch executive or a collation authority can amend this result.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            tally_serializer = ResultSubmissionSerializer(
                data=request.data, partial=True
            )
            tally_serializer.is_valid(raise_exception=True)
            submission.tallies = [
                CandidateTally(candidate=t["candidate_id"], votes=t["votes"])
                for t in tally_serializer.validated_data.get("tallies", [])
            ]

        for field in (
            "collation_sheet_photo_base64",
            "total_registered_voters",
            "total_valid_votes",
            "total_rejected_votes",
        ):
            if field in request.data and (is_submitter or has_authority):
                setattr(submission, field, request.data[field])

        submission.save()
        log_action(
            request.user,
            "elections.result.update",
            request=request,
            target=submission,
            description=f"status={submission.status}",
        )
        return Response(ResultSubmissionSerializer(submission).data)


class ResultSummaryView(APIView):
    """
    GET /api/v1/elections/<election_id>/results/summary/?organizational_unit_id=&position=

    Automatic, real-time collation and analysis: per-candidate totals and
    percentages, turnout, and reporting completeness (how many of the
    expected polling stations have reported), rolled up from every Branch
    in the given unit's subtree. Point this at the National unit for the
    national picture, or at any Region/Constituency for a local view -
    the exact same computation, just a different subtree.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["elections"])
    def get(self, request, election_id):
        from apps.elections.views_elections import _get_election_or_404

        election = _get_election_or_404(election_id)

        unit_id = request.query_params.get("organizational_unit_id")
        unit = election.scope_unit
        if unit_id:
            try:
                unit = OrganizationalUnit.objects.get(id=unit_id, is_active=True)
            except (DoesNotExist, MongoValidationError) as exc:
                raise APIError(
                    "Organizational unit not found.",
                    code="not_found",
                    http_status=status.HTTP_404_NOT_FOUND,
                ) from exc

        position = request.query_params.get("position")
        return Response(aggregate_results(election, unit, position=position))
