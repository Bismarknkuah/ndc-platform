from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.documents.documents import PartyDocument
from apps.documents.permissions import can_manage_documents, can_view_document
from apps.documents.serializers import (
    PartyDocumentListItemSerializer,
    PartyDocumentSerializer,
)


def _get_document_or_404(document_id):
    try:
        return PartyDocument.objects.get(id=document_id, is_active=True)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Document not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class PartyDocumentListCreateView(APIView):
    """
    GET  /api/v1/documents/?category=&organizational_unit_id=
         Documents visible to the caller: public-within-party documents,
         plus anything scoped to a unit in their own ancestor chain (their
         unit and everything above it) or their own descendant subtree.
         List responses omit the file payload; fetch the detail view to
         download.

    POST /api/v1/documents/
         Upload a document scoped to an organizational unit
         (hierarchy.manage authority over that unit required).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: PartyDocumentListItemSerializer(many=True)}, tags=["documents"]
    )
    def get(self, request):
        user = request.user
        if user.is_superadmin:
            qs = PartyDocument.objects(is_active=True)
        else:
            visible_unit_ids = []
            if user.organizational_unit:
                visible_unit_ids = [
                    u.id
                    for u in (
                        [user.organizational_unit]
                        + user.organizational_unit.get_ancestors()
                    )
                ]
                from apps.messaging.services import units_in_subtree

                visible_unit_ids += [
                    u.id for u in units_in_subtree(user.organizational_unit)
                ]
            qs = PartyDocument.objects(
                is_active=True,
                __raw__={
                    "$or": [
                        {"is_public_within_party": True},
                        {"organizational_unit": {"$in": visible_unit_ids}},
                    ]
                },
            )

        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        organizational_unit_id = request.query_params.get("organizational_unit_id")
        if organizational_unit_id:
            qs = qs.filter(organizational_unit=organizational_unit_id)

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            PartyDocumentListItemSerializer(page, many=True).data
        )

    @extend_schema(
        request=PartyDocumentSerializer,
        responses={201: PartyDocumentSerializer},
        tags=["documents"],
    )
    def post(self, request):
        serializer = PartyDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["organizational_unit_id"]

        if not can_manage_documents(request.user, target_unit):
            raise APIError(
                "You do not have authority to upload documents for this unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        document = PartyDocument.objects.create(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            category=serializer.validated_data["category"],
            organizational_unit=target_unit,
            uploaded_by=request.user,
            file_base64=serializer.validated_data["file_base64"],
            file_name=serializer.validated_data["file_name"],
            mime_type=serializer.validated_data["mime_type"],
            is_public_within_party=serializer.validated_data.get(
                "is_public_within_party", False
            ),
        )
        log_action(
            request.user,
            "documents.document.upload",
            request=request,
            target=document,
            description=document.title,
        )
        return Response(
            PartyDocumentSerializer(document).data, status=status.HTTP_201_CREATED
        )


class PartyDocumentDetailView(APIView):
    """GET/DELETE /api/v1/documents/<id>/ - download (full payload) or soft-delete."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PartyDocumentSerializer}, tags=["documents"])
    def get(self, request, document_id):
        document = _get_document_or_404(document_id)
        if not can_view_document(request.user, document):
            raise APIError(
                "You do not have access to this document.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return Response(PartyDocumentSerializer(document).data)

    @extend_schema(responses={204: None}, tags=["documents"])
    def delete(self, request, document_id):
        document = _get_document_or_404(document_id)
        if not can_manage_documents(request.user, document.organizational_unit):
            raise APIError(
                "You do not have authority to delete this document.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        document.is_active = False
        document.save()
        log_action(
            request.user,
            "documents.document.delete",
            request=request,
            target=document,
            description=document.title,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
