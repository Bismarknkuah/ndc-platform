import datetime

from mongoengine import DateTimeField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument

DIRECTIVE_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("ACKNOWLEDGED", "Acknowledged"),
    ("COMPLETED", "Completed"),
]


class LeaderDirective(TimestampedDocument):
    """
    A task the party's national leadership (Flagbearer, National
    Chairman) assigns directly to any executive - National, Regional, or
    District/Constituency level - independent of department structure.
    Deliberately a separate model from apps.departments.documents.
    TaskAssignment: that one is a department's own internal diary
    ("go be on Joy FM's morning show"), required to belong to a specific
    Department. A leader's directive is a different kind of thing - it
    doesn't need a department at all, and retrofitting TaskAssignment to
    make department optional would touch a lot of already-working,
    tested code for something conceptually distinct anyway.
    """

    assigned_to = ReferenceField(User, required=True)
    assigned_by = ReferenceField(User, required=True)

    title = StringField(required=True, max_length=200)
    description = StringField(default="")
    due_at = DateTimeField(null=True)

    status = StringField(choices=DIRECTIVE_STATUS_CHOICES, default="PENDING")
    acknowledged_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)

    meta = {
        "collection": "leader_directives",
        "indexes": ["assigned_to", "assigned_by", "status", "-created_at"],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"{self.title} -> {self.assigned_to.full_name}"

    def mark_acknowledged(self):
        self.status = "ACKNOWLEDGED"
        self.acknowledged_at = datetime.datetime.utcnow()

    def mark_completed(self):
        self.status = "COMPLETED"
        self.completed_at = datetime.datetime.utcnow()
