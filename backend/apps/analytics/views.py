from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.permissions import can_view_analytics, can_view_ground_intelligence
from apps.analytics.services import (
    compute_department_analytics,
    compute_ground_intelligence,
    compute_membership_analytics,
)
from apps.core.exceptions import APIError
from apps.departments.documents import Department
from apps.hierarchy.documents import OrganizationalUnit
from apps.messaging.services import units_in_subtree


def _get_unit_or_404(unit_id):
    try:
        return OrganizationalUnit.objects.get(id=unit_id, is_active=True)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Organizational unit not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


def _get_department_or_404(department_id):
    try:
        return Department.objects.get(id=department_id, is_active=True)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Department not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class MembershipAnalyticsView(APIView):
    """
    GET /api/v1/analytics/membership/?organizational_unit_id=

    Real aggregation over the actual membership data in a unit's subtree:
    total count, gender breakdown, executive vs ordinary member split, and
    month-by-month growth over the last 12 months (from date_joined).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["analytics"])
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
                "You do not have authority to view analytics for this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return Response(compute_membership_analytics(unit))


class DepartmentAnalyticsView(APIView):
    """
    GET /api/v1/analytics/departments/?department_id=&organizational_unit_id=

    Task completion analytics for a department's team at a unit: total
    tasks assigned, pending/acknowledged/completed/cancelled breakdown,
    and a completion rate.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["analytics"])
    def get(self, request):
        department_id = request.query_params.get("department_id")
        organizational_unit_id = request.query_params.get("organizational_unit_id")
        if not department_id or not organizational_unit_id:
            raise APIError(
                "department_id and organizational_unit_id are both required.",
                code="invalid_input",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        department = _get_department_or_404(department_id)
        unit = _get_unit_or_404(organizational_unit_id)

        from apps.departments.permissions import has_department_authority

        if not (
            can_view_analytics(request.user, unit)
            or has_department_authority(request.user, department, unit)
        ):
            raise APIError(
                "You do not have authority to view analytics for this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return Response(compute_department_analytics(department, unit))


class GISMapView(APIView):
    """
    GET /api/v1/analytics/map/?organizational_unit_id=&unit_type=

    Every unit with GIS coordinates set, within a jurisdiction's subtree,
    as a simple GeoJSON-style FeatureCollection ready for a map library
    (Leaflet, Mapbox, Google Maps) on the client. Only units that have
    actually had latitude/longitude set are returned - this endpoint
    doesn't guess coordinates or call any geocoding service.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["analytics"])
    def get(self, request):
        organizational_unit_id = request.query_params.get("organizational_unit_id")
        if not organizational_unit_id:
            raise APIError(
                "organizational_unit_id is required.",
                code="invalid_input",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        unit = _get_unit_or_404(organizational_unit_id)

        unit_type = request.query_params.get("unit_type")
        candidates = units_in_subtree(unit)
        if unit_type:
            candidates = [u for u in candidates if u.unit_type == unit_type]

        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [u.longitude, u.latitude]},
                "properties": {
                    "id": str(u.id),
                    "name": u.name,
                    "unit_type": u.unit_type,
                },
            }
            for u in candidates
            if u.latitude is not None and u.longitude is not None
        ]

        return Response({"type": "FeatureCollection", "features": features})


class GroundIntelligenceView(APIView):
    """
    GET /api/v1/analytics/ground-intelligence/<unit_id>/

    Real, aggregated complaint/welfare/report data for a unit and its
    whole subtree - the actual ground situation, not a guess. Deliberately
    a narrower audience than the jurisdiction rollup every executive
    already gets for their own unit: this reaches into any unit the
    caller selects, not just their own, so it's gated on
    analytics.ground_intelligence specifically (Flagbearer, National
    Chairman) rather than the general hierarchy.manage check.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["analytics"])
    def get(self, request, unit_id):
        if not can_view_ground_intelligence(request.user):
            raise APIError(
                "Ground Intelligence is only available to the party's national "
                "leadership.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        unit = _get_unit_or_404(unit_id)
        return Response(compute_ground_intelligence(unit))
