import base64
import io

import qrcode

from apps.accounts.documents import User
from apps.membership.documents import MembershipCard

QR_PREFIX = "NDC-MEMBER-CARD:"


def get_or_create_card(user: User) -> MembershipCard:
    card = MembershipCard.objects(user=user).first()
    if card is None:
        card = MembershipCard.objects.create(user=user)
    return card


def generate_qr_code_base64(token: str) -> str:
    """Returns a base64-encoded PNG (no data: prefix) for embedding in JSON/HTML."""
    payload = f"{QR_PREFIX}{token}"
    img = qrcode.make(payload, box_size=8, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def verify_token(raw_value: str):
    """
    Accepts either a bare token or a full scanned QR payload
    ("NDC-MEMBER-CARD:<token>"). Returns the MembershipCard if the token
    corresponds to an active card belonging to an active member, else None.
    """
    token = (
        raw_value[len(QR_PREFIX) :] if raw_value.startswith(QR_PREFIX) else raw_value
    )
    card = MembershipCard.objects(token=token, is_active=True).first()
    if card is None or not card.user.is_active:
        return None
    return card
