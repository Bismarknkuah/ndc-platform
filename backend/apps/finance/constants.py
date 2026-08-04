RECORD_TYPE_CHOICES = [
    ("INCOME", "Income"),
    ("EXPENSE", "Expense"),
]

RECORD_STATUS_CHOICES = [
    ("PENDING", "Pending Approval"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
]

# Free-form category is allowed, but these are the common ones surfaced
# in UI dropdowns.
COMMON_CATEGORIES = [
    "Membership Dues",
    "Donations",
    "Fundraising Event",
    "Event Costs",
    "Campaign Materials",
    "Travel & Logistics",
    "Administrative",
    "Salaries & Stipends",
    "Other",
]
