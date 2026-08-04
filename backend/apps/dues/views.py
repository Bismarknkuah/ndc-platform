import datetime
import uuid

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.dues.documents import DuesPayment
from apps.dues.serializers import DuesPaymentSerializer, InitializeDuesPaymentSerializer
from apps.dues.services import (
    initialize_transaction,
    verify_transaction,
    verify_webhook_signature,
)


def _reference() -> str:
    return f"NDC-DUES-{uuid.uuid4().hex[:20]}"


def _apply_verification_result(payment: DuesPayment, result: dict):
    """Shared by both the explicit verify endpoint and the webhook - one
    place that actually mutates a DuesPayment's status and creates the
    matching FinanceRecord, so the two entry points can never diverge in
    behavior."""
    if payment.status == "SUCCESS":
        return

    if not result["success"]:
        payment.status = "FAILED"
        payment.save()
        return

    payment.status = "SUCCESS"
    payment.payment_method = result.get("channel")
    payment.paid_at = datetime.datetime.utcnow()

    from apps.finance.documents import FinanceRecord

    finance_record = FinanceRecord.objects.create(
        record_type="INCOME",
        category="Membership Dues",
        amount=payment.amount,
        currency=payment.currency,
        description=f"Dues payment ({payment.period}) from {payment.user.full_name}",
        organizational_unit=payment.user.organizational_unit,
        recorded_by=payment.user,
        status="APPROVED",
    )
    finance_record.approved_by = payment.user
    finance_record.approved_at = datetime.datetime.utcnow()
    finance_record.save()

    payment.finance_record = finance_record
    payment.save()


class InitializeDuesPaymentView(APIView):
    """POST /api/v1/dues/initialize/ - a member pays their own dues.
    Returns a Paystack-hosted checkout URL supporting Mobile Money (MTN
    and others), bank transfer, and card - this app never collects card
    or MoMo details directly."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=InitializeDuesPaymentSerializer,
        responses={200: OpenApiTypes.OBJECT},
        tags=["dues"],
    )
    def post(self, request):
        serializer = InitializeDuesPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        period = data.get("period") or datetime.datetime.utcnow().strftime("%Y-%m")
        reference = _reference()

        callback_url = request.data.get("callback_url") or ""
        result = initialize_transaction(
            reference=reference,
            email=request.user.email,
            amount_cedis=data["amount"],
            callback_url=callback_url,
        )
        if result is None:
            raise APIError(
                "Dues payment isn't available right now - the payment "
                "provider isn't configured or the request failed. Try "
                "again shortly.",
                code="payment_unavailable",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        DuesPayment.objects.create(
            user=request.user,
            amount=data["amount"],
            period=period,
            paystack_reference=reference,
        )
        log_action(request.user, "dues.payment.initialize", request=request)
        return Response(
            {
                "authorization_url": result["authorization_url"],
                "reference": reference,
            }
        )


class VerifyDuesPaymentView(APIView):
    """GET /api/v1/dues/verify/<reference>/ - explicit check, for the
    frontend to call right after the member returns from Paystack's
    checkout (doesn't solely rely on the webhook, which can be delayed
    or occasionally not delivered)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: DuesPaymentSerializer}, tags=["dues"])
    def get(self, request, reference):
        try:
            payment = DuesPayment.objects.get(paystack_reference=reference)
        except DoesNotExist as exc:
            raise APIError(
                "Payment not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if (
            str(payment.user.id) != str(request.user.id)
            and not request.user.is_superadmin
        ):
            raise APIError(
                "You don't have access to this payment.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if payment.status == "PENDING":
            result = verify_transaction(reference)
            if result is not None:
                _apply_verification_result(payment, result)
                payment.reload()

        return Response(DuesPaymentSerializer(payment).data)


class DuesPaymentWebhookView(APIView):
    """POST /api/v1/dues/webhook/ - Paystack's own server-to-server
    notification. No user auth (Paystack isn't a logged-in user) -
    authenticated instead via HMAC signature verification, which is
    Paystack's documented webhook security model."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT}, tags=["dues"]
    )
    def post(self, request):
        signature = request.headers.get("x-paystack-signature")
        if not verify_webhook_signature(request.body, signature):
            raise APIError(
                "Invalid webhook signature.",
                code="invalid_signature",
                http_status=status.HTTP_401_UNAUTHORIZED,
            )

        event = request.data.get("event")
        if event != "charge.success":
            return Response({"received": True})

        reference = request.data.get("data", {}).get("reference")
        try:
            payment = DuesPayment.objects.get(paystack_reference=reference)
        except DoesNotExist:
            return Response({"received": True})

        result = verify_transaction(reference)
        if result is not None:
            _apply_verification_result(payment, result)

        return Response({"received": True})


class DuesPaymentHistoryView(APIView):
    """GET /api/v1/dues/history/ - the caller's own payment history."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: DuesPaymentSerializer(many=True)}, tags=["dues"])
    def get(self, request):
        qs = DuesPayment.objects(user=request.user).order_by("-created_at")
        paginator, page = paginate_queryset(qs, request, self)
        return paginator.get_paginated_response(
            DuesPaymentSerializer(page, many=True).data
        )
