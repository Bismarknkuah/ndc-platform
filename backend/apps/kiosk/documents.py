from mongoengine import BooleanField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.elections.documents import Election
from apps.hierarchy.documents import OrganizationalUnit


class VotingKiosk(TimestampedDocument):
    """
    A registered, physical walk-up voting terminal for one election - not
    an open endpoint anyone can call. `kiosk_code` identifies which real,
    known device/location is making a request; it is deliberately not
    treated as a secret (the real security boundary is each voter's own
    Kiosk PIN, something only they know and set themselves through their
    authenticated account - see User.set_kiosk_pin). Registering kiosks
    lets a stolen laptop or a copy-pasted URL be immediately shut off by
    deactivating just that one kiosk, without touching anyone's account.
    """

    election = ReferenceField(Election, required=True)
    unit = ReferenceField(OrganizationalUnit, required=True)
    label = StringField(required=True, max_length=150)
    kiosk_code = StringField(required=True, unique=True, max_length=32)
    created_by = ReferenceField(User, required=True)
    is_active = BooleanField(default=True)

    meta = {
        "collection": "voting_kiosks",
        "indexes": ["election", "unit", "kiosk_code"],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"{self.label} ({self.kiosk_code})"
