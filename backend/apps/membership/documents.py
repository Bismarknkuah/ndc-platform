import datetime
import secrets

from mongoengine import BooleanField, DateTimeField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument


def _generate_token():
    return secrets.token_urlsafe(32)


class MembershipCard(TimestampedDocument):
    """
    One active card per member. The QR code printed/displayed on the card
    encodes `token` (never the membership_id alone, which is guessable) so
    that scanning it can prove card authenticity via verify_membership().
    Reissuing (lost card, security rotation) invalidates the old token.
    """

    user = ReferenceField(User, required=True, unique=True)
    token = StringField(required=True, unique=True, default=_generate_token)
    issued_at = DateTimeField(default=datetime.datetime.utcnow)
    expires_at = DateTimeField(null=True)
    is_active = BooleanField(default=True)

    meta = {
        "collection": "membership_cards",
        "indexes": [
            {"fields": ["user"], "unique": True},
            {"fields": ["token"], "unique": True},
        ],
    }

    def rotate_token(self):
        self.token = _generate_token()
        self.issued_at = datetime.datetime.utcnow()

    def __str__(self):
        return f"Card for {self.user.membership_id}"
