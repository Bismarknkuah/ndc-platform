from django.urls import path

from apps.chatbot.views import (
    ChatConversationDetailView,
    ChatConversationListCreateView,
    ChatMessageListCreateView,
)

urlpatterns = [
    path(
        "conversations/",
        ChatConversationListCreateView.as_view(),
        name="chat-conversation-list-create",
    ),
    path(
        "conversations/<str:conversation_id>/",
        ChatConversationDetailView.as_view(),
        name="chat-conversation-detail",
    ),
    path(
        "conversations/<str:conversation_id>/messages/",
        ChatMessageListCreateView.as_view(),
        name="chat-message-list-create",
    ),
]
