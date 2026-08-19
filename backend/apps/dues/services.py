"""
Paystack integration for membership dues. Deliberately uses Paystack's
own hosted checkout (the `authorization_url` returned by initialize)
rather than collecting card/MoMo details directly in this app - Paystack
handles PCI compliance and the actual MTN/bank/card processing; this
codebase never sees or stores a real card number or MoMo PIN.

Every function here returns None on any failure (missing config,
network error, non-2xx response) - callers must surface a clear
"payment unavailable" response, never fabricate a successful payment.
"""

import hashlib
import hmac
import logging

from django.conf import settings

from apps.dues.constants import PESEWAS_PER_CEDI

logger = logging.getLogger("ndc")

PAYSTACK_API_URL = "https://api.paystack.co"


def initialize_transaction(
    reference: str, email: str, amount_cedis, callback_url: str
) -> dict | None:
    """Returns {"authorization_url": ..., "access_code": ...} or None."""
    if not settings.PAYSTACK_SECRET_KEY:
        logger.info(
            "Dues payment initialize skipped (PAYSTACK_SECRET_KEY not configured)"
        )
        return None

    try:
        import requests

        response = requests.post(
            f"{PAYSTACK_API_URL}/transaction/initialize",
            headers={
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "email": email,
                "amount": int(amount_cedis * PESEWAS_PER_CEDI),
                "currency": "GHS",
                "reference": reference,
                "callback_url": callback_url,
                "channels": ["card", "mobile_money", "bank_transfer", "bank"],
            },
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("status"):
            logger.error("Paystack initialize returned status=false: %s", body)
            return None
        data = body["data"]
        return {
            "authorization_url": data["authorization_url"],
            "access_code": data["access_code"],
        }
    except Exception:
        logger.exception("Paystack initialize_transaction failed")
        return None


def verify_transaction(reference: str) -> dict | None:
    """Returns {"success": bool, "channel": str, "amount_cedis": Decimal,
    "paid_at": str|None} or None if the verify call itself failed."""
    if not settings.PAYSTACK_SECRET_KEY:
        logger.info("Dues payment verify skipped (PAYSTACK_SECRET_KEY not configured)")
        return None

    try:
        import requests

        response = requests.get(
            f"{PAYSTACK_API_URL}/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("status"):
            return None
        data = body["data"]
        return {
            "success": data.get("status") == "success",
            "channel": data.get("channel"),
            "amount_cedis": data.get("amount", 0) / PESEWAS_PER_CEDI,
            "paid_at": data.get("paid_at"),
        }
    except Exception:
        logger.exception("Paystack verify_transaction failed")
        return None


def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Paystack signs webhook payloads with HMAC-SHA512 of the raw request
    body, using the secret key - verify this before trusting anything in
    a webhook call, since it has no other authentication."""
    if not settings.PAYSTACK_SECRET_KEY or not signature_header:
        return False
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"), raw_body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
