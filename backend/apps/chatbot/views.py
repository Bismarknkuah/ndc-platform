from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.chatbot.documents import ChatConversation, ChatMessage
from apps.chatbot.serializers import (
    ChatConversationSerializer,
    ChatMessageSerializer,
    SendChatMessageSerializer,
)
from apps.chatbot.services import generate_chat_reply


def _get_own_conversation_or_404(request, conversation_id):
    try:
        conversation = ChatConversation.objects.get(id=conversation_id, is_active=True)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Conversation not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc
    if conversation.user.id != request.user.id and not request.user.is_superadmin:
        raise APIError(
            "This isn't your conversation.",
            code="forbidden",
            http_status=status.HTTP_403_FORBIDDEN,
        )
    return conversation


class ChatConversationListCreateView(APIView):
    """
    GET  /api/v1/chatbot/conversations/ - the caller's own conversations,
         most recently updated first. Available to every authenticated
         user - there is no permission gate on this feature.

    POST /api/v1/chatbot/conversations/ - start a new conversation.
         Optional {"title": "..."}; defaults to "New conversation".
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "chat"

    @extend_schema(
        responses={200: ChatConversationSerializer(many=True)}, tags=["chatbot"]
    )
    def get(self, request):
        qs = ChatConversation.objects(user=request.user, is_active=True).order_by(
            "-updated_at"
        )
        paginator, page = paginate_queryset(qs, request, self)
        return paginator.get_paginated_response(
            ChatConversationSerializer(page, many=True).data
        )

    @extend_schema(
        request=ChatConversationSerializer,
        responses={201: ChatConversationSerializer},
        tags=["chatbot"],
    )
    def post(self, request):
        title = request.data.get("title") or "New conversation"
        conversation = ChatConversation.objects.create(user=request.user, title=title)
        log_action(
            request.user,
            "chatbot.conversation.create",
            request=request,
            target=conversation,
        )
        return Response(
            ChatConversationSerializer(conversation).data,
            status=status.HTTP_201_CREATED,
        )


class ChatConversationDetailView(APIView):
    """DELETE /api/v1/chatbot/conversations/<id>/ - archive (soft-delete) a conversation."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None}, tags=["chatbot"])
    def delete(self, request, conversation_id):
        conversation = _get_own_conversation_or_404(request, conversation_id)
        conversation.is_active = False
        conversation.save()
        log_action(
            request.user,
            "chatbot.conversation.archive",
            request=request,
            target=conversation,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatMessageListCreateView(APIView):
    """
    GET  /api/v1/chatbot/conversations/<id>/messages/ - full message
         history for one of the caller's own conversations, oldest first.

    POST /api/v1/chatbot/conversations/<id>/messages/ {"body": "..."} -
         send a message and get the assistant's reply synchronously.
         Returns both messages (user's, then assistant's) so the
         frontend doesn't need a second round-trip. Returns 503 if
         AI-assisted chat isn't configured on this deployment
         (ANTHROPIC_API_KEY missing) or the provider call fails - the
         user's message is still saved either way, so nothing is lost.
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "chat"

    @extend_schema(responses={200: ChatMessageSerializer(many=True)}, tags=["chatbot"])
    def get(self, request, conversation_id):
        conversation = _get_own_conversation_or_404(request, conversation_id)
        qs = ChatMessage.objects(conversation=conversation).order_by("created_at")
        paginator, page = paginate_queryset(qs, request, self)
        return paginator.get_paginated_response(
            ChatMessageSerializer(page, many=True).data
        )

    @extend_schema(
        request=SendChatMessageSerializer,
        responses={
            201: OpenApiTypes.OBJECT,
            503: OpenApiResponse(
                description="AI-assisted chat is not configured or unavailable"
            ),
        },
        tags=["chatbot"],
    )
    def post(self, request, conversation_id):
        conversation = _get_own_conversation_or_404(request, conversation_id)
        serializer = SendChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_message = ChatMessage.objects.create(
            conversation=conversation,
            role="USER",
            body=serializer.validated_data["body"],
        )

        # First message in a conversation still titled "New conversation"?
        # Use it (truncated) as a friendlier auto-title, same idea as
        # most chat products.
        if conversation.title == "New conversation":
            conversation.title = user_message.body[:60]
        conversation.save()  # bumps updated_at regardless, for sort order

        history = [
            {"role": m.role, "body": m.body}
            for m in ChatMessage.objects(conversation=conversation).order_by(
                "created_at"
            )
        ]
        reply_text = generate_chat_reply(request.user, history)

        if reply_text is None:
            raise APIError(
                "The platform assistant isn't configured on this deployment "
                "(ANTHROPIC_API_KEY missing) or the request to the AI provider failed. "
                "Your message was saved.",
                code="chat_unavailable",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        assistant_message = ChatMessage.objects.create(
            conversation=conversation, role="ASSISTANT", body=reply_text
        )

        return Response(
            {
                "user_message": ChatMessageSerializer(user_message).data,
                "assistant_message": ChatMessageSerializer(assistant_message).data,
            },
            status=status.HTTP_201_CREATED,
        )
