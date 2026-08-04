from mongoengine import DictField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.hierarchy.documents import OrganizationalUnit

REPORT_TYPE_CHOICES = [
    ("MEMBERSHIP", "Membership"),
    ("DEPARTMENT", "Department"),
    ("FINANCE", "Finance"),
]


class AIGeneratedReport(TimestampedDocument):
    """A record of one AI-assisted executive summary - kept for audit/
    history, since these are advisory text generated from real party data
    and party officers may want to reference what was said and when."""

    report_type = StringField(required=True, choices=REPORT_TYPE_CHOICES)
    organizational_unit = ReferenceField(OrganizationalUnit, required=True)
    generated_by = ReferenceField(User, required=True)
    source_data = DictField(required=True)
    summary_text = StringField(required=True)
    model_used = StringField(required=True)

    meta = {
        "collection": "ai_generated_reports",
        "indexes": ["organizational_unit", "report_type", "-created_at"],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"AI {self.report_type} report for {self.organizational_unit.name}"
