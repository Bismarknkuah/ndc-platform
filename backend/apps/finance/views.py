from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.finance.documents import FinanceRecord
from apps.finance.permissions import can_manage_finance, can_view_finance
from apps.finance.serializers import FinanceRecordSerializer
from apps.finance.services import summarize_finance
from apps.hierarchy.documents import OrganizationalUnit


def _get_record_or_404(record_id):
    try:
        return FinanceRecord.objects.get(id=record_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Finance record not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class FinanceRecordListCreateView(APIView):
    """
    GET  /api/v1/finance/records/?organizational_unit_id=&record_type=&status=
         Lists finance records within a unit's subtree (finance.view/manage
         authority over that unit required).

    POST /api/v1/finance/records/
         Record an income or expense entry (finance.manage authority over
         the target unit required). Starts PENDING.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: FinanceRecordSerializer(many=True)}, tags=["finance"]
    )
    def get(self, request):
        organizational_unit_id = request.query_params.get("organizational_unit_id")
        if not organizational_unit_id:
            raise APIError(
                "organizational_unit_id is required.",
                code="invalid_input",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
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
        if not can_view_finance(request.user, unit):
            raise APIError(
                "You do not have finance authority over this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        from apps.finance.services import units_in_subtree

        unit_ids = [u.id for u in units_in_subtree(unit)]
        qs = FinanceRecord.objects(organizational_unit__in=unit_ids)

        record_type = request.query_params.get("record_type")
        if record_type:
            qs = qs.filter(record_type=record_type)
        record_status = request.query_params.get("status")
        if record_status:
            qs = qs.filter(status=record_status)

        paginator, page = paginate_queryset(qs.order_by("-record_date"), request, self)
        return paginator.get_paginated_response(
            FinanceRecordSerializer(page, many=True).data
        )

    @extend_schema(
        request=FinanceRecordSerializer,
        responses={201: FinanceRecordSerializer},
        tags=["finance"],
    )
    def post(self, request):
        serializer = FinanceRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["organizational_unit_id"]

        if not can_manage_finance(request.user, target_unit):
            raise APIError(
                "You do not have authority to record finance entries for this unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        record = FinanceRecord.objects.create(
            record_type=serializer.validated_data["record_type"],
            category=serializer.validated_data["category"],
            amount=serializer.validated_data["amount"],
            currency=serializer.validated_data.get("currency", "GHS"),
            description=serializer.validated_data.get("description", ""),
            organizational_unit=target_unit,
            recorded_by=request.user,
            record_date=serializer.validated_data.get("record_date"),
            receipt_photo_base64=serializer.validated_data.get("receipt_photo_base64"),
        )
        log_action(
            request.user,
            "finance.record.create",
            request=request,
            target=record,
            description=f"{record.record_type} {record.currency}{record.amount} - {record.category}",
        )
        return Response(
            FinanceRecordSerializer(record).data, status=status.HTTP_201_CREATED
        )


class FinanceRecordDetailView(APIView):
    """GET/PATCH /api/v1/finance/records/<id>/ - view or approve/reject/amend a record."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: FinanceRecordSerializer}, tags=["finance"])
    def get(self, request, record_id):
        record = _get_record_or_404(record_id)
        if not can_view_finance(request.user, record.organizational_unit):
            raise APIError(
                "You do not have finance authority over this record.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return Response(FinanceRecordSerializer(record).data)

    @extend_schema(
        request=FinanceRecordSerializer,
        responses={200: FinanceRecordSerializer},
        tags=["finance"],
    )
    def patch(self, request, record_id):
        record = _get_record_or_404(record_id)
        has_authority = can_manage_finance(request.user, record.organizational_unit)
        is_recorder = record.recorded_by.id == request.user.id

        new_status = request.data.get("status")
        if new_status in ("APPROVED", "REJECTED"):
            if not has_authority:
                raise APIError(
                    "Only finance authority for this unit can approve/reject a record.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            if new_status == "APPROVED":
                record.mark_approved(request.user)
            else:
                record.mark_rejected(request.user)

        for field in ("category", "amount", "description", "receipt_photo_base64"):
            if field in request.data and (is_recorder or has_authority):
                setattr(record, field, request.data[field])

        record.save()
        log_action(
            request.user,
            "finance.record.update",
            request=request,
            target=record,
            description=f"status={record.status}",
        )
        return Response(FinanceRecordSerializer(record).data)


class FinanceSummaryView(APIView):
    """
    GET /api/v1/finance/summary/?organizational_unit_id=&start_date=&end_date=&status=

    Automatic roll-up: total income, total expense, net balance, and a
    breakdown by category, aggregated across every unit in the given
    unit's subtree. Defaults to APPROVED records only.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["finance"])
    def get(self, request):
        organizational_unit_id = request.query_params.get("organizational_unit_id")
        if not organizational_unit_id:
            raise APIError(
                "organizational_unit_id is required.",
                code="invalid_input",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
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
        if not can_view_finance(request.user, unit):
            raise APIError(
                "You do not have finance authority over this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        record_status = request.query_params.get("status", "APPROVED")
        if record_status == "ALL":
            record_status = None
        return Response(summarize_finance(unit, status=record_status))
