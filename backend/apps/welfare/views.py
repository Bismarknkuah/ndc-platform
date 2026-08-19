from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.welfare.documents import WelfareRequest
from apps.welfare.permissions import can_manage_welfare
from apps.welfare.serializers import WelfareRequestSerializer


def _get_request_or_404(request_id):
    try:
        return WelfareRequest.objects.get(id=request_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Welfare request not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class WelfareRequestListCreateView(APIView):
    """
    GET  /api/v1/welfare/requests/?status=&organizational_unit_id=
         Own requests, or (with finance/hierarchy authority) every request
         within a jurisdiction's subtree.

    POST /api/v1/welfare/requests/
         Any member can request welfare support for themselves, filed at
         their own organizational unit.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: WelfareRequestSerializer(many=True)}, tags=["welfare"]
    )
    def get(self, request):
        organizational_unit_id = request.query_params.get("organizational_unit_id")
        if organizational_unit_id:
            from apps.hierarchy.documents import OrganizationalUnit

            try:
                unit = OrganizationalUnit.objects.get(
                    id=organizational_unit_id, is_active=True
                )
            except (DoesNotExist, MongoValidationError) as exc:
                raise APIError(
                    "Organizational unit not found.",
                    code="not_found",
                    http_status=status.HTTP_404_NOT_FOUND,
                ) from exc
            if not can_manage_welfare(request.user, unit):
                raise APIError(
                    "You do not have welfare authority over this jurisdiction.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )

            from apps.messaging.services import units_in_subtree

            unit_ids = [u.id for u in units_in_subtree(unit)]
            qs = WelfareRequest.objects(organizational_unit__in=unit_ids)
        else:
            qs = WelfareRequest.objects(requester=request.user)

        request_status = request.query_params.get("status")
        if request_status:
            qs = qs.filter(status=request_status)

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            WelfareRequestSerializer(page, many=True).data
        )

    @extend_schema(
        request=WelfareRequestSerializer,
        responses={201: WelfareRequestSerializer},
        tags=["welfare"],
    )
    def post(self, request):
        if request.user.organizational_unit is None:
            raise APIError(
                "You are not attached to an organizational unit.", code="invalid_state"
            )

        serializer = WelfareRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        welfare_request = WelfareRequest.objects.create(
            requester=request.user,
            organizational_unit=request.user.organizational_unit,
            category=serializer.validated_data["category"],
            description=serializer.validated_data["description"],
            amount_requested=serializer.validated_data["amount_requested"],
            supporting_document_base64=serializer.validated_data.get(
                "supporting_document_base64"
            ),
        )
        log_action(
            request.user,
            "welfare.request.submit",
            request=request,
            target=welfare_request,
            description=welfare_request.category,
        )
        return Response(
            WelfareRequestSerializer(welfare_request).data,
            status=status.HTTP_201_CREATED,
        )


class WelfareRequestDetailView(APIView):
    """
    GET   /api/v1/welfare/requests/<id>/
    PATCH /api/v1/welfare/requests/<id>/  - authority reviews/approves/
          rejects/disburses. Marking DISBURSED automatically creates a
          matching FinanceRecord expense entry (APPROVED, category
          "Welfare Support") so the payout is never invisible to the books.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: WelfareRequestSerializer}, tags=["welfare"])
    def get(self, request, request_id):
        welfare_request = _get_request_or_404(request_id)
        if not (
            request.user.is_superadmin
            or welfare_request.requester.id == request.user.id
            or can_manage_welfare(request.user, welfare_request.organizational_unit)
        ):
            raise APIError(
                "You do not have access to this request.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return Response(WelfareRequestSerializer(welfare_request).data)

    @extend_schema(
        request=WelfareRequestSerializer,
        responses={200: WelfareRequestSerializer},
        tags=["welfare"],
    )
    def patch(self, request, request_id):
        welfare_request = _get_request_or_404(request_id)
        new_status = request.data.get("status")

        if new_status in ("UNDER_REVIEW", "APPROVED", "REJECTED", "DISBURSED"):
            if not can_manage_welfare(
                request.user, welfare_request.organizational_unit
            ):
                raise APIError(
                    "Only welfare authority for this unit can update this request's status.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )

            if new_status == "DISBURSED" and welfare_request.finance_record is None:
                from apps.finance.documents import FinanceRecord

                finance_record = FinanceRecord.objects.create(
                    record_type="EXPENSE",
                    category="Welfare Support",
                    amount=welfare_request.amount_requested,
                    description=(
                        f"Welfare disbursement to {welfare_request.requester.full_name} "
                        f"({welfare_request.category})"
                    ),
                    organizational_unit=welfare_request.organizational_unit,
                    recorded_by=request.user,
                    status="APPROVED",
                )
                finance_record.approved_by = request.user
                import datetime

                finance_record.approved_at = datetime.datetime.utcnow()
                finance_record.save()
                welfare_request.finance_record = finance_record

            welfare_request.mark_reviewed(
                request.user, new_status, notes=request.data.get("resolution_notes", "")
            )

        welfare_request.save()
        log_action(
            request.user,
            "welfare.request.update",
            request=request,
            target=welfare_request,
            description=f"status={welfare_request.status}",
        )
        return Response(WelfareRequestSerializer(welfare_request).data)
