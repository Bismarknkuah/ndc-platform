from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.messaging.documents import Notification, NotificationPreference
from apps.messaging.serializers import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
)


class NotificationListView(APIView):
    """GET /api/v1/messaging/notifications/?unread=true - the caller's notification inbox."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: NotificationSerializer(many=True)}, tags=["messaging"]
    )
    def get(self, request):
        qs = Notification.objects(user=request.user)
        if request.query_params.get("unread") == "true":
            qs = qs.filter(is_read=False)
        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            NotificationSerializer(page, many=True).data
        )


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["messaging"])
    def get(self, request):
        count = Notification.objects(user=request.user, is_read=False).count()
        return Response({"unread_count": count})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: NotificationSerializer}, tags=["messaging"]
    )
    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id, user=request.user
            )
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Notification not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if not notification.is_read:
            notification.mark_read()
            notification.save()
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: OpenApiTypes.OBJECT}, tags=["messaging"]
    )
    def post(self, request):
        import datetime

        updated = Notification.objects(user=request.user, is_read=False).update(
            is_read=True, read_at=datetime.datetime.utcnow()
        )
        return Response({"marked_read": updated})


class NotificationPreferenceView(APIView):
    """GET/PUT /api/v1/messaging/notification-preferences/ - manage your own delivery channel opt-ins."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: NotificationPreferenceSerializer}, tags=["messaging"]
    )
    def get(self, request):
        preference = NotificationPreference.objects(user=request.user).first()
        if preference is None:
            preference = NotificationPreference.objects.create(user=request.user)
        return Response(NotificationPreferenceSerializer(preference).data)

    @extend_schema(
        request=NotificationPreferenceSerializer,
        responses={200: NotificationPreferenceSerializer},
        tags=["messaging"],
    )
    def put(self, request):
        serializer = NotificationPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        preference = NotificationPreference.objects(user=request.user).first()
        if preference is None:
            preference = NotificationPreference(user=request.user)

        for field in ("email_enabled", "sms_enabled", "push_enabled", "push_token"):
            if field in serializer.validated_data:
                setattr(preference, field, serializer.validated_data[field])
        preference.save()
        return Response(NotificationPreferenceSerializer(preference).data)
