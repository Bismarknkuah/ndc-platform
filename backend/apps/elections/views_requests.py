from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.elections.documents import ElectionRequest
from apps.elections.permissions import can_manage_election, can_request_election
from apps.elections.serializers import (
    ElectionRequestReviewSerializer,
    ElectionRequestSerializer,
)
from apps.hierarchy.documents import OrganizationalUnit
from apps.messaging.services import units_in_subtree


def _get_request_or_404(request_id):
    try:
        return ElectionRequest.objects.get(id=request_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Election request not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class ElectionRequestListCreateView(APIView):
    """
    GET  /api/v1/elections/requests/?status=&target_unit_id=
         List election requests. An ordinary requester sees only their
         own; an Election/IT Director (can_manage_election over a unit)
         sees every request within their jurisdiction, so they have a
         real queue to work from rather than requests arriving with no
         way to find them again.

    POST /api/v1/elections/requests/
         A department or unit executive asks the Election/IT Director
         to organize an election for them - the only route left open to
         them now that organizing authority is centralized (see
         can_manage_election's docstring).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: ElectionRequestSerializer(many=True)}, tags=["elections"]
    )
    def get(self, request):
        qs = ElectionRequest.objects.all()

        target_unit_id = request.query_params.get("target_unit_id")
        if target_unit_id:
            try:
                unit = OrganizationalUnit.objects.get(id=target_unit_id, is_active=True)
            except (DoesNotExist, MongoValidationError) as exc:
                raise APIError(
                    "Organizational unit not found.",
                    code="not_found",
                    http_status=status.HTTP_404_NOT_FOUND,
                ) from exc
            if not can_manage_election(request.user, unit):
                raise APIError(
                    "You do not have authority to view requests across this "
                    "jurisdiction.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            unit_ids = [u.id for u in units_in_subtree(unit)]
            qs = qs.filter(target_unit__in=unit_ids)
        else:
            # No jurisdiction given: an organizer sees everything (their
            # real review queue), everyone else only ever sees their own
            # requests, never someone else's.
            if not can_manage_election(request.user, request.user.organizational_unit):
                qs = qs.filter(requested_by=request.user)

        result_status = request.query_params.get("status")
        if result_status:
            qs = qs.filter(status=result_status)

        qs = qs.order_by("-created_at")
        paginator, page = paginate_queryset(qs, request, self)
        return paginator.get_paginated_response(
            ElectionRequestSerializer(page, many=True).data
        )

    @extend_schema(
        request=ElectionRequestSerializer,
        responses={201: ElectionRequestSerializer},
        tags=["elections"],
    )
    def post(self, request):
        serializer = ElectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_unit = data["target_unit_id"]
        if not can_request_election(request.user, target_unit):
            raise APIError(
                "You do not have authority to request an election for this unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        election_request = ElectionRequest.objects.create(
            requested_by=request.user,
            target_unit=target_unit,
            election_type=data["election_type"],
            title=data["title"],
            reason=data["reason"],
            requested_start_date=data.get("requested_start_date"),
            requested_end_date=data.get("requested_end_date"),
        )
        log_action(request.user, "elections.request.create", request=request)
        return Response(
            ElectionRequestSerializer(election_request).data,
            status=status.HTTP_201_CREATED,
        )


class ElectionRequestDetailView(APIView):
    """
    GET   /api/v1/elections/requests/<id>/
    PATCH /api/v1/elections/requests/<id>/  {"status": "APPROVED"|"REJECTED", "notes": "..."}
          The Election/IT Director approves or rejects a request. To
          actually fulfill an approved request, create the real
          Election via POST /api/v1/elections/ with a
          "fulfills_request_id" field - that's what links the request
          to a real, organized election, not this endpoint.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ElectionRequestSerializer}, tags=["elections"])
    def get(self, request, request_id):
        election_request = _get_request_or_404(request_id)
        if election_request.requested_by != request.user and not can_manage_election(
            request.user, election_request.target_unit
        ):
            raise APIError(
                "You do not have authority to view this request.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return Response(ElectionRequestSerializer(election_request).data)

    @extend_schema(
        request=ElectionRequestReviewSerializer,
        responses={200: ElectionRequestSerializer},
        tags=["elections"],
    )
    def patch(self, request, request_id):
        election_request = _get_request_or_404(request_id)
        if not can_manage_election(request.user, election_request.target_unit):
            raise APIError(
                "Only the Election/IT Director has authority to review "
                "this request.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if election_request.status != "PENDING":
            raise APIError(
                "This request has already been reviewed.",
                code="already_reviewed",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        new_status = request.data.get("status")
        notes = request.data.get("notes", "")
        if new_status == "APPROVED":
            election_request.approve(request.user, notes)
        elif new_status == "REJECTED":
            election_request.reject(request.user, notes)
        else:
            raise APIError(
                "status must be APPROVED or REJECTED.",
                code="invalid_status",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        log_action(
            request.user,
            "elections.request.review",
            request=request,
            description=f"status={new_status}",
        )
        return Response(ElectionRequestSerializer(election_request).data)
