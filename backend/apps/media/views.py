from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.media.documents import MediaAsset
from apps.media.permissions import can_manage_media, can_view_media
from apps.media.serializers import MediaAssetListItemSerializer, MediaAssetSerializer


def _get_asset_or_404(asset_id):
    try:
        return MediaAsset.objects.get(id=asset_id, is_active=True)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Media asset not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class MediaAssetListCreateView(APIView):
    """
    GET  /api/v1/media/?media_type=&event_id=&tag=&organizational_unit_id=
         Same visibility rule as documents: public-within-party assets,
         plus anything in the caller's own ancestor chain or descendant
         subtree. List responses omit the file payload.

    POST /api/v1/media/
         Upload media scoped to an organizational unit (hierarchy.manage
         authority over that unit required).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: MediaAssetListItemSerializer(many=True)}, tags=["media"]
    )
    def get(self, request):
        user = request.user
        if user.is_superadmin:
            qs = MediaAsset.objects(is_active=True)
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
            qs = MediaAsset.objects(
                is_active=True,
                __raw__={
                    "$or": [
                        {"is_public_within_party": True},
                        {"organizational_unit": {"$in": visible_unit_ids}},
                    ]
                },
            )

        media_type = request.query_params.get("media_type")
        if media_type:
            qs = qs.filter(media_type=media_type)
        event_id = request.query_params.get("event_id")
        if event_id:
            qs = qs.filter(event=event_id)
        tag = request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags=tag)
        organizational_unit_id = request.query_params.get("organizational_unit_id")
        if organizational_unit_id:
            qs = qs.filter(organizational_unit=organizational_unit_id)

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            MediaAssetListItemSerializer(page, many=True).data
        )

    @extend_schema(
        request=MediaAssetSerializer,
        responses={201: MediaAssetSerializer},
        tags=["media"],
    )
    def post(self, request):
        serializer = MediaAssetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["organizational_unit_id"]

        if not can_manage_media(request.user, target_unit):
            raise APIError(
                "You do not have authority to upload media for this unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        asset = MediaAsset.objects.create(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            media_type=serializer.validated_data["media_type"],
            tags=serializer.validated_data.get("tags", []),
            organizational_unit=target_unit,
            uploaded_by=request.user,
            event=serializer.validated_data.get("event_id"),
            file_base64=serializer.validated_data.get("file_base64"),
            external_url=serializer.validated_data.get("external_url"),
            is_public_within_party=serializer.validated_data.get(
                "is_public_within_party", False
            ),
        )
        log_action(
            request.user,
            "media.asset.upload",
            request=request,
            target=asset,
            description=asset.title,
        )
        return Response(
            MediaAssetSerializer(asset).data, status=status.HTTP_201_CREATED
        )


class MediaAssetDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MediaAssetSerializer}, tags=["media"])
    def get(self, request, asset_id):
        asset = _get_asset_or_404(asset_id)
        if not can_view_media(request.user, asset):
            raise APIError(
                "You do not have access to this media asset.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return Response(MediaAssetSerializer(asset).data)

    @extend_schema(responses={204: None}, tags=["media"])
    def delete(self, request, asset_id):
        asset = _get_asset_or_404(asset_id)
        if not can_manage_media(request.user, asset.organizational_unit):
            raise APIError(
                "You do not have authority to delete this media asset.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        asset.is_active = False
        asset.save()
        log_action(
            request.user,
            "media.asset.delete",
            request=request,
            target=asset,
            description=asset.title,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
