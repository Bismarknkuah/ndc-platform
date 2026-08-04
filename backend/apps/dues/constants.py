"""
Membership dues payment, via Paystack (supports Ghana natively and
handles Mobile Money - including MTN - bank transfer, and card payment
all through one hosted checkout, rather than three separate merchant
integrations). Reasoned default given the party asked for exactly these
three methods; requires a real Paystack merchant account and
PAYSTACK_SECRET_KEY to actually process real money - see
apps/dues/services.py.
"""

DUES_PAYMENT_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("SUCCESS", "Success"),
    ("FAILED", "Failed"),
    ("ABANDONED", "Abandoned"),
]

# Paystack's own "channel" values on a verified transaction - stored
# as-is rather than re-mapped, so this list is really just documentation
# of what to expect, not an exhaustive enum Paystack is bound by.
PAYMENT_METHOD_CHOICES = [
    ("mobile_money", "Mobile Money"),
    ("bank_transfer", "Bank Transfer"),
    ("card", "Card"),
    ("bank", "Bank"),
    ("qr", "QR"),
    ("ussd", "USSD"),
]

# Paystack expects amounts in the smallest currency unit (pesewas for
# GHS), not the naira/cedi-equivalent - this factor converts a
# human-entered GHS amount to what Paystack's API actually wants.
PESEWAS_PER_CEDI = 100
