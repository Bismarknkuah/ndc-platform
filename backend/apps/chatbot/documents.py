from mongoengine import (
    BooleanField,
    ReferenceField,
    StringField,
    CASCADE,
)

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.chatbot.constants import MESSAGE_ROLE_CHOICES


class ChatConversation(TimestampedDocument):
    """
    A single chat thread between one member and the platform assistant.
    Every member - any role, any level - can start one; there is no
    permission gate on this feature by design (it exists specifically to
    be available to every type of user).
    """

    user = ReferenceField(User, required=True)
    title = StringField(max_length=200, default="New conversation")
    is_active = BooleanField(default=True)

    meta = {
        "collection": "chat_conversations",
        "indexes": ["user", "-created_at"],
    }


class ChatMessage(TimestampedDocument):
    """One message in a conversation - either the member's own message or
    the assistant's reply. Assistant replies are generated synchronously
    at send-time (see apps.chatbot.services.generate_chat_reply) and
    stored so the conversation has a durable history, not just an
    ephemeral one held in the frontend's state."""

    conversation = ReferenceField(
        ChatConversation, required=True, reverse_delete_rule=CASCADE
    )
    role = StringField(choices=MESSAGE_ROLE_CHOICES, required=True)
    body = StringField(required=True)

    meta = {
        "collection": "chat_messages",
        "indexes": ["conversation", "created_at"],
    }
