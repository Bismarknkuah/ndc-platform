from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRolePermission
from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.hierarchy.documents import OrganizationalUnit
from apps.hierarchy.serializers import OrganizationalUnitSerializer

CanManageHierarchy = HasRolePermission.requiring("hierarchy.manage")


def _get_unit_or_404(unit_id):
    try:
        return OrganizationalUnit.objects.get(id=unit_id, is_active=True)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Organizational unit not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class OrganizationalUnitListCreateView(APIView):
    """
    GET  /api/v1/hierarchy/units/?unit_type=&parent_id=&search=
    POST /api/v1/hierarchy/units/   (requires hierarchy.manage permission)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), CanManageHierarchy()]
        return [IsAuthenticated()]

    @extend_schema(
        operation_id="hierarchy_units_list",
        responses={200: OrganizationalUnitSerializer(many=True)},
        tags=["hierarchy"],
    )
    def get(self, request):
        qs = OrganizationalUnit.objects(is_active=True)

        unit_type = request.query_params.get("unit_type")
        if unit_type:
            qs = qs.filter(unit_type=unit_type)

        parent_id = request.query_params.get("parent_id")
        if parent_id:
            qs = qs.filter(parent=parent_id)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)

        paginator, page = paginate_queryset(qs.order_by("name"), request, self)
        data = OrganizationalUnitSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @extend_schema(
        operation_id="hierarchy_units_create",
        request=OrganizationalUnitSerializer,
        responses={201: OrganizationalUnitSerializer},
        tags=["hierarchy"],
    )
    def post(self, request):
        serializer = OrganizationalUnitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unit = serializer.save()
        log_action(
            request.user,
            "hierarchy.unit.create",
            request=request,
            target=unit,
            description=f"Created {unit.unit_type} '{unit.name}'",
        )
        return Response(
            OrganizationalUnitSerializer(unit).data, status=status.HTTP_201_CREATED
        )


class OrganizationalUnitDetailView(APIView):
    """
    GET/PATCH/DELETE /api/v1/hierarchy/units/<id>/
    DELETE performs a soft delete (is_active=False) to preserve audit/history integrity.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), CanManageHierarchy()]

    @extend_schema(
        operation_id="hierarchy_units_retrieve",
        responses={200: OrganizationalUnitSerializer},
        tags=["hierarchy"],
    )
    def get(self, request, unit_id):
        unit = _get_unit_or_404(unit_id)
        return Response(OrganizationalUnitSerializer(unit).data)

    @extend_schema(
        operation_id="hierarchy_units_update",
        request=OrganizationalUnitSerializer,
        responses={200: OrganizationalUnitSerializer},
        tags=["hierarchy"],
    )
    def patch(self, request, unit_id):
        unit = _get_unit_or_404(unit_id)
        serializer = OrganizationalUnitSerializer(unit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        log_action(
            request.user, "hierarchy.unit.update", request=request, target=updated
        )
        return Response(OrganizationalUnitSerializer(updated).data)

    @extend_schema(
        operation_id="hierarchy_units_deactivate",
        responses={204: None},
        tags=["hierarchy"],
    )
    def delete(self, request, unit_id):
        unit = _get_unit_or_404(unit_id)
        if unit.get_children().count() > 0:
            raise APIError(
                "Cannot deactivate a unit that still has active child units.",
                code="conflict",
                http_status=status.HTTP_409_CONFLICT,
            )
        unit.is_active = False
        unit.save()
        log_action(
            request.user, "hierarchy.unit.deactivate", request=request, target=unit
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationalUnitDescendantsView(APIView):
    """GET /api/v1/hierarchy/units/<id>/descendants/ - full subtree, flat list."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OrganizationalUnitSerializer(many=True)}, tags=["hierarchy"]
    )
    def get(self, request, unit_id):
        unit = _get_unit_or_404(unit_id)
        descendants = unit.get_descendants()
        return Response(OrganizationalUnitSerializer(descendants, many=True).data)


class OrganizationalUnitAncestorsView(APIView):
    """GET /api/v1/hierarchy/units/<id>/ancestors/ - breadcrumb from parent up to root."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OrganizationalUnitSerializer(many=True)}, tags=["hierarchy"]
    )
    def get(self, request, unit_id):
        unit = _get_unit_or_404(unit_id)
        ancestors = unit.get_ancestors()
        return Response(OrganizationalUnitSerializer(ancestors, many=True).data)
