from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.complaints.documents import Complaint, PetitionSupport
from apps.complaints.permissions import can_manage_complaint, can_view_complaint
from apps.complaints.serializers import ComplaintSerializer


def _get_complaint_or_404(complaint_id):
    try:
        return Complaint.objects.get(id=complaint_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Complaint not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class ComplaintListCreateView(APIView):
    """
    GET  /api/v1/complaints/?complaint_type=&status=&target_unit_id=
         Complaints visible to the caller: submitted by them, assigned to
         them, or addressed to their own unit / an ancestor of it.

    POST /api/v1/complaints/
         File a complaint or petition from the caller's own unit, addressed
         to that unit or an ancestor of it - same rule as upward reports.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ComplaintSerializer(many=True)}, tags=["complaints"])
    def get(self, request):
        user = request.user
        if user.is_superadmin:
            qs = Complaint.objects.all()
        else:
            qs = Complaint.objects(
                __raw__={
                    "$or": [
                        {"submitted_by": user.id},
                        {"assigned_to": user.id},
                        {
                            "target_unit": (
                                user.organizational_unit.id
                                if user.organizational_unit
                                else None
                            )
                        },
                    ]
                }
            )

        complaint_type = request.query_params.get("complaint_type")
        if complaint_type:
            qs = qs.filter(complaint_type=complaint_type)
        complaint_status = request.query_params.get("status")
        if complaint_status:
            qs = qs.filter(status=complaint_status)
        target_unit_id = request.query_params.get("target_unit_id")
        if target_unit_id:
            qs = qs.filter(target_unit=target_unit_id)

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            ComplaintSerializer(page, many=True).data
        )

    @extend_schema(
        request=ComplaintSerializer,
        responses={201: ComplaintSerializer},
        tags=["complaints"],
    )
    def post(self, request):
        if request.user.organizational_unit is None:
            raise APIError(
                "You are not attached to an organizational unit.", code="invalid_state"
            )

        serializer = ComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["target_unit_id"]
        submitting_unit = request.user.organizational_unit

        if not (
            target_unit.id == submitting_unit.id
            or target_unit.is_ancestor_of(submitting_unit)
        ):
            raise APIError(
                "Complaints/petitions may only be addressed to your own unit or an ancestor of it.",
                code="invalid_target",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        complaint = Complaint.objects.create(
            submitted_by=request.user,
            submitting_unit=submitting_unit,
            target_unit=target_unit,
            complaint_type=serializer.validated_data["complaint_type"],
            subject=serializer.validated_data["subject"],
            description=serializer.validated_data["description"],
        )
        log_action(
            request.user,
            "complaints.complaint.submit",
            request=request,
            target=complaint,
            description=complaint.subject,
        )
        return Response(
            ComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED
        )


class ComplaintDetailView(APIView):
    """GET/PATCH /api/v1/complaints/<id>/ - view, assign, resolve, or dismiss."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ComplaintSerializer}, tags=["complaints"])
    def get(self, request, complaint_id):
        complaint = _get_complaint_or_404(complaint_id)
        if not can_view_complaint(request.user, complaint):
            raise APIError(
                "You do not have access to this complaint.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return Response(ComplaintSerializer(complaint).data)

    @extend_schema(
        request=ComplaintSerializer,
        responses={200: ComplaintSerializer},
        tags=["complaints"],
    )
    def patch(self, request, complaint_id):
        complaint = _get_complaint_or_404(complaint_id)
        if not can_manage_complaint(request.user, complaint.target_unit):
            raise APIError(
                "Only the target office (or an office above it) can manage this complaint.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if "assigned_to_id" in request.data:
            from apps.accounts.documents import User

            try:
                complaint.assigned_to = User.objects.get(
                    id=request.data["assigned_to_id"], is_active=True
                )
            except (DoesNotExist, MongoValidationError) as exc:
                raise APIError(
                    "User not found.",
                    code="not_found",
                    http_status=status.HTTP_404_NOT_FOUND,
                ) from exc

        new_status = request.data.get("status")
        if new_status in ("UNDER_REVIEW", "RESOLVED", "DISMISSED"):
            complaint.status = new_status
            if new_status in ("RESOLVED", "DISMISSED"):
                import datetime

                complaint.resolved_by = request.user
                complaint.resolved_at = datetime.datetime.utcnow()
                complaint.resolution_notes = request.data.get(
                    "resolution_notes", complaint.resolution_notes
                )

        complaint.save()
        log_action(
            request.user,
            "complaints.complaint.update",
            request=request,
            target=complaint,
            description=f"status={complaint.status}",
        )
        return Response(ComplaintSerializer(complaint).data)


class PetitionSupportView(APIView):
    """POST /api/v1/complaints/<id>/support/ - co-sign a petition."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={201: None}, tags=["complaints"])
    def post(self, request, complaint_id):
        complaint = _get_complaint_or_404(complaint_id)
        if complaint.complaint_type != "PETITION":
            raise APIError(
                "Only petitions can be co-signed.",
                code="invalid_type",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        support, created = None, False
        existing = PetitionSupport.objects(
            complaint=complaint, user=request.user
        ).first()
        if existing is None:
            support = PetitionSupport.objects.create(
                complaint=complaint, user=request.user
            )
            created = True
        else:
            support = existing

        supporter_count = PetitionSupport.objects(complaint=complaint).count()
        return Response(
            {
                "id": str(support.id),
                "supporter_count": supporter_count,
                "already_signed": not created,
            },
            status=status.HTTP_201_CREATED,
        )
