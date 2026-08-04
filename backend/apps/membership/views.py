from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.membership.serializers import (
    MembershipCardSerializer,
    VerifyCardRequestSerializer,
    VerifyCardResponseSerializer,
)
from apps.membership.services import (
    generate_qr_code_base64,
    get_or_create_card,
    verify_token,
)


def _card_representation(card):
    user = card.user
    return {
        "membership_id": user.membership_id,
        "full_name": user.full_name,
        "role": user.role.name if user.role else "",
        "organizational_unit": (
            user.organizational_unit.name if user.organizational_unit else ""
        ),
        "issued_at": card.issued_at.isoformat(),
        "expires_at": card.expires_at.isoformat() if card.expires_at else None,
        "qr_code_base64": generate_qr_code_base64(card.token),
    }


class MyMembershipCardView(APIView):
    """GET /api/v1/membership/card/ - the authenticated member's digital membership card, QR included."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MembershipCardSerializer}, tags=["membership"])
    def get(self, request):
        card = get_or_create_card(request.user)
        return Response(_card_representation(card))


class ReissueMembershipCardView(APIView):
    """POST /api/v1/membership/card/reissue/ - rotates the QR token (lost card / security precaution)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: MembershipCardSerializer}, tags=["membership"]
    )
    def post(self, request):
        card = get_or_create_card(request.user)
        card.rotate_token()
        card.save()
        log_action(
            request.user, "membership.card.reissue", request=request, target=card
        )
        return Response(_card_representation(card))


class VerifyMembershipCardView(APIView):
    """
    POST /api/v1/membership/verify/
    Scan-a-card endpoint for meeting registration desks / polling agents:
    submit the scanned QR payload (or bare token) and get back whether the
    card is valid plus the member's identity.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=VerifyCardRequestSerializer,
        responses={200: VerifyCardResponseSerializer},
        tags=["membership"],
    )
    def post(self, request):
        serializer = VerifyCardRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        card = verify_token(serializer.validated_data["token"])

        if card is None:
            log_action(request.user, "membership.card.verify_failed", request=request)
            return Response({"valid": False})

        log_action(
            request.user, "membership.card.verify_success", request=request, target=card
        )
        user = card.user
        return Response(
            {
                "valid": True,
                "membership_id": user.membership_id,
                "full_name": user.full_name,
                "role": user.role.name if user.role else "",
                "organizational_unit": (
                    user.organizational_unit.name if user.organizational_unit else ""
                ),
            }
        )
