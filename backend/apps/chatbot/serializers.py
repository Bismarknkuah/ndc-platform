from rest_framework import serializers

from apps.chatbot.constants import MESSAGE_ROLE_CHOICES


class ChatConversationSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200, required=False)
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "title": instance.title,
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
        }


class ChatMessageSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    role = serializers.ChoiceField(choices=MESSAGE_ROLE_CHOICES, read_only=True)
    body = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "role": instance.role,
            "body": instance.body,
            "created_at": instance.created_at.isoformat(),
        }


class SendChatMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=4000, allow_blank=False)
