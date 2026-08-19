from rest_framework import serializers


class MembershipCardSerializer(serializers.Serializer):
    membership_id = serializers.CharField()
    full_name = serializers.CharField()
    role = serializers.CharField()
    organizational_unit = serializers.CharField()
    issued_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(allow_null=True)
    qr_code_base64 = serializers.CharField()


class VerifyCardRequestSerializer(serializers.Serializer):
    token = serializers.CharField()


class VerifyCardResponseSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    membership_id = serializers.CharField(required=False)
    full_name = serializers.CharField(required=False)
    role = serializers.CharField(required=False)
    organizational_unit = serializers.CharField(required=False)
