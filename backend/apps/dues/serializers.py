from decimal import Decimal

from rest_framework import serializers


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class DuesPaymentSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "user": _user_summary(instance.user),
            "amount": str(instance.amount),
            "currency": instance.currency,
            "period": instance.period,
            "status": instance.status,
            "payment_method": instance.payment_method,
            "paystack_reference": instance.paystack_reference,
            "paid_at": instance.paid_at.isoformat() if instance.paid_at else None,
            "created_at": instance.created_at.isoformat(),
        }


class InitializeDuesPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("1")
    )
    period = serializers.CharField(
        required=False,
        help_text="e.g. '2026-08' for August 2026. Defaults to the current month.",
    )
