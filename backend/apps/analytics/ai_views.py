from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.ai_reporting import DEFAULT_MODEL, generate_summary
from apps.analytics.ai_serializers import (
    AIGeneratedReportSerializer,
    GenerateAIReportSerializer,
)
from apps.analytics.documents import AIGeneratedReport
from apps.analytics.permissions import can_view_analytics
from apps.analytics.services import (
    compute_department_analytics,
    compute_membership_analytics,
)
from apps.analytics.views import _get_department_or_404, _get_unit_or_404
from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset


class AIReportListCreateView(APIView):
    """
    GET  /api/v1/analytics/ai-report/?organizational_unit_id=&report_type=
         History of previously generated AI summaries for a jurisdiction.

    POST /api/v1/analytics/ai-report/
         Generates a fresh natural-language executive summary from this
         platform's own real aggregated data (never raw member records)
         via the Anthropic API. Requires ANTHROPIC_API_KEY to be
         configured; otherwise returns a clear 503 rather than a fake
         summary.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: AIGeneratedReportSerializer(many=True)}, tags=["analytics"]
    )
    def get(self, request):
        organizational_unit_id = request.query_params.get("organizational_unit_id")
        if not organizational_unit_id:
            raise APIError(
                "organizational_unit_id is required.",
                code="invalid_input",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        unit = _get_unit_or_404(organizational_unit_id)
        if not can_view_analytics(request.user, unit):
            raise APIError(
                "You do not have authority to view AI reports for this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        qs = AIGeneratedReport.objects(organizational_unit=unit)
        report_type = request.query_params.get("report_type")
        if report_type:
            qs = qs.filter(report_type=report_type)

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            AIGeneratedReportSerializer(page, many=True).data
        )

    @extend_schema(
        request=GenerateAIReportSerializer,
        responses={201: AIGeneratedReportSerializer},
        tags=["analytics"],
    )
    def post(self, request):
        serializer = GenerateAIReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unit = serializer.validated_data["organizational_unit_id"]
        report_type = serializer.validated_data["report_type"]
        department_id = serializer.validated_data.get("department_id")

        if not can_view_analytics(request.user, unit):
            raise APIError(
                "You do not have authority to generate AI reports for this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        source_data = self._gather_source_data(report_type, unit, department_id)

        summary_text = generate_summary(report_type, source_data)
        if summary_text is None:
            raise APIError(
                "AI-assisted reporting is not configured on this deployment (ANTHROPIC_API_KEY missing) "
                "or the request to the AI provider failed.",
                code="ai_unavailable",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        report = AIGeneratedReport.objects.create(
            report_type=report_type,
            organizational_unit=unit,
            generated_by=request.user,
            source_data=source_data,
            summary_text=summary_text,
            model_used=DEFAULT_MODEL,
        )
        log_action(
            request.user,
            "analytics.ai_report.generate",
            request=request,
            target=report,
            description=report_type,
        )
        return Response(
            AIGeneratedReportSerializer(report).data, status=status.HTTP_201_CREATED
        )

    @staticmethod
    def _gather_source_data(report_type, unit, department_id):
        if report_type == "MEMBERSHIP":
            return compute_membership_analytics(unit)

        if report_type == "DEPARTMENT":
            if not department_id:
                raise APIError(
                    "department_id is required for a DEPARTMENT report.",
                    code="invalid_input",
                    http_status=status.HTTP_400_BAD_REQUEST,
                )
            department = _get_department_or_404(department_id)
            return compute_department_analytics(department, unit)

        if report_type == "FINANCE":
            from apps.finance.services import summarize_finance

            return summarize_finance(unit)

        raise APIError(
            "Unsupported report_type.",
            code="invalid_input",
            http_status=status.HTTP_400_BAD_REQUEST,
        )
