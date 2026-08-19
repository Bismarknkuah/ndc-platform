from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.messaging.documents import Report
from apps.messaging.permissions import can_manage_report, can_submit_report
from apps.messaging.serializers import ReportSerializer


def _get_report_or_404(report_id):
    try:
        return Report.objects.get(id=report_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Report not found.", code="not_found", http_status=status.HTTP_404_NOT_FOUND
        ) from exc


class ReportListCreateView(APIView):
    """
    GET  /api/v1/messaging/reports/?status=&target_unit_id=&submitting_unit_id=
         Reports visible to the caller: submitted by them, addressed to
         their own unit, or addressed to any unit their own unit is an
         ancestor of.

    POST /api/v1/messaging/reports/
         File an upward report from the caller's own unit to an ancestor
         unit (e.g. Branch -> Constituency, or straight to National).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ReportSerializer(many=True)}, tags=["messaging"])
    def get(self, request):
        user = request.user
        if user.is_superadmin:
            qs = Report.objects.all()
        else:
            qs = Report.objects(
                __raw__={
                    "$or": [
                        {"submitted_by": user.id},
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

        report_status = request.query_params.get("status")
        if report_status:
            qs = qs.filter(status=report_status)

        target_unit_id = request.query_params.get("target_unit_id")
        if target_unit_id:
            qs = qs.filter(target_unit=target_unit_id)

        submitting_unit_id = request.query_params.get("submitting_unit_id")
        if submitting_unit_id:
            qs = qs.filter(submitting_unit=submitting_unit_id)

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(ReportSerializer(page, many=True).data)

    @extend_schema(
        request=ReportSerializer, responses={201: ReportSerializer}, tags=["messaging"]
    )
    def post(self, request):
        if not can_submit_report(request.user):
            raise APIError(
                "Your role does not carry upward-reporting permission.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if request.user.organizational_unit is None:
            raise APIError(
                "You are not attached to an organizational unit.", code="invalid_state"
            )

        serializer = ReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["target_unit_id"]
        submitting_unit = request.user.organizational_unit

        if not (
            target_unit.id == submitting_unit.id
            or target_unit.is_ancestor_of(submitting_unit)
        ):
            raise APIError(
                "Reports may only be addressed to your own unit or an ancestor of it.",
                code="invalid_target",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        report = Report.objects.create(
            title=serializer.validated_data["title"],
            body=serializer.validated_data["body"],
            submitted_by=request.user,
            submitting_unit=submitting_unit,
            target_unit=target_unit,
        )

        from apps.messaging.services import notify_many

        notify_many(
            _direct_members(target_unit),
            "REPORT",
            title=f"New report from {submitting_unit.name}: {report.title}",
            body=report.body[:200],
            target=report,
        )

        log_action(
            request.user,
            "messaging.report.submit",
            request=request,
            target=report,
            description=f"{submitting_unit.name} -> {target_unit.name}: {report.title}",
        )
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


def _direct_members(unit):
    from apps.accounts.documents import User

    return list(User.objects(organizational_unit=unit, is_active=True))


class ReportDetailView(APIView):
    """
    GET   /api/v1/messaging/reports/<id>/
    PATCH /api/v1/messaging/reports/<id>/  - target office (or an ancestor
          of it) acknowledges or resolves the report.
    """

    permission_classes = [IsAuthenticated]

    def _check_view(self, request, report):
        if (
            request.user.is_superadmin
            or report.submitted_by.id == request.user.id
            or can_manage_report(request.user, report)
        ):
            return
        raise APIError(
            "You do not have access to this report.",
            code="forbidden",
            http_status=status.HTTP_403_FORBIDDEN,
        )

    @extend_schema(responses={200: ReportSerializer}, tags=["messaging"])
    def get(self, request, report_id):
        report = _get_report_or_404(report_id)
        self._check_view(request, report)
        return Response(ReportSerializer(report).data)

    @extend_schema(
        request=ReportSerializer, responses={200: ReportSerializer}, tags=["messaging"]
    )
    def patch(self, request, report_id):
        report = _get_report_or_404(report_id)
        new_status = request.data.get("status")

        if new_status in ("ACKNOWLEDGED", "RESOLVED"):
            if not can_manage_report(request.user, report):
                raise APIError(
                    "Only the report's target office (or an office above it) can update its status.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            report.status = new_status
            if new_status == "RESOLVED":
                report.resolved_by = request.user
                if "resolution_notes" in request.data:
                    report.resolution_notes = request.data["resolution_notes"]
            report.save()
            log_action(
                request.user,
                "messaging.report.update",
                request=request,
                target=report,
                description=f"status={new_status}",
            )

        return Response(ReportSerializer(report).data)
