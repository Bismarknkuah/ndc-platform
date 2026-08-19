import datetime

from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.messaging.documents import DirectMessage
from apps.messaging.serializers import DirectMessageSerializer
from apps.messaging.services import notify


class DirectMessageListCreateView(APIView):
    """
    GET  /api/v1/messaging/direct-messages/?with=<user_id> - conversation with a specific user
         (omit `with` to get every message sent to/from the caller, newest first)
    POST /api/v1/messaging/direct-messages/ - send a message
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: DirectMessageSerializer(many=True)}, tags=["messaging"]
    )
    def get(self, request):
        user = request.user
        with_user_id = request.query_params.get("with")
        if with_user_id:
            from bson import ObjectId
            from bson.errors import InvalidId

            try:
                other_id = ObjectId(with_user_id)
            except InvalidId as exc:
                raise APIError(
                    "Invalid user id.",
                    code="invalid_id",
                    http_status=status.HTTP_400_BAD_REQUEST,
                ) from exc
            qs = DirectMessage.objects(
                __raw__={
                    "$or": [
                        {"sender": user.id, "recipient": other_id},
                        {"sender": other_id, "recipient": user.id},
                    ]
                }
            )
        else:
            qs = DirectMessage.objects(
                __raw__={"$or": [{"sender": user.id}, {"recipient": user.id}]}
            )

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            DirectMessageSerializer(page, many=True).data
        )

    @extend_schema(
        request=DirectMessageSerializer,
        responses={201: DirectMessageSerializer},
        tags=["messaging"],
    )
    def post(self, request):
        serializer = DirectMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipient = serializer.validated_data["recipient_id"]

        if recipient.id == request.user.id:
            raise APIError(
                "You cannot message yourself.",
                code="invalid_recipient",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        message = DirectMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            body=serializer.validated_data["body"],
        )
        notify(
            recipient,
            "DIRECT_MESSAGE",
            title=f"Message from {request.user.full_name}",
            body=message.body[:200],
            target=message,
        )
        return Response(
            DirectMessageSerializer(message).data, status=status.HTTP_201_CREATED
        )


class DirectMessageMarkReadView(APIView):
    """POST /api/v1/messaging/direct-messages/<id>/read/ - recipient marks a message as read."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: DirectMessageSerializer}, tags=["messaging"]
    )
    def post(self, request, message_id):
        try:
            message = DirectMessage.objects.get(id=message_id)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Message not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

        if message.recipient.id != request.user.id:
            raise APIError(
                "Only the recipient can mark a message as read.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if message.read_at is None:
            message.read_at = datetime.datetime.utcnow()
            message.save()
        return Response(DirectMessageSerializer(message).data)
