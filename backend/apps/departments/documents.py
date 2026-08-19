import datetime

from mongoengine import BooleanField, DateTimeField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.departments.constants import (
    ENGAGEMENT_TYPE_CHOICES,
    POSITION_CHOICES,
    TASK_STATUS_CHOICES,
)
from apps.hierarchy.documents import OrganizationalUnit


class Department(TimestampedDocument):
    """A functional department, e.g. Communications, Finance, Organizing."""

    name = StringField(required=True, max_length=150)
    code = StringField(
        required=True, unique=True, max_length=64
    )  # e.g. "communications"
    description = StringField(default="")
    is_active = BooleanField(default=True)

    meta = {
        "collection": "departments",
        "indexes": [{"fields": ["code"], "unique": True}],
        "ordering": ["name"],
    }

    def __str__(self):
        return self.name


class DepartmentAssignment(TimestampedDocument):
    """
    Places a User into a Department's chain of command at a specific
    OrganizationalUnit, e.g. (Kofi, Communications, Ashanti Region, HEAD)
    represents "Kofi is the Ashanti Regional Communications Director".
    """

    user = ReferenceField(User, required=True)
    department = ReferenceField(Department, required=True)
    organizational_unit = ReferenceField(OrganizationalUnit, required=True)
    position = StringField(required=True, choices=POSITION_CHOICES)

    appointed_by = ReferenceField(User, null=True)
    is_active = BooleanField(default=True)

    meta = {
        "collection": "department_assignments",
        "indexes": [
            "user",
            "department",
            "organizational_unit",
            ("department", "organizational_unit", "is_active"),
        ],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"{self.user.full_name} - {self.position} - {self.department.name} @ {self.organizational_unit.name}"


class TaskAssignment(TimestampedDocument):
    """
    A diary entry: "go be on Joy FM's morning show on 2026-07-10" assigned
    by a department head/deputy to one of their department's members.
    """

    department = ReferenceField(Department, required=True)
    assigned_to = ReferenceField(User, required=True)
    assigned_by = ReferenceField(User, required=True)

    title = StringField(required=True, max_length=200)
    description = StringField(default="")
    engagement_type = StringField(required=True, choices=ENGAGEMENT_TYPE_CHOICES)
    platform_name = StringField(
        max_length=150, default=""
    )  # e.g. "Joy FM", "GTV", "Citi TV"
    location = StringField(max_length=200, default="")

    scheduled_at = DateTimeField(required=True)

    status = StringField(choices=TASK_STATUS_CHOICES, default="PENDING")
    acknowledged_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)

    meta = {
        "collection": "department_task_assignments",
        "indexes": [
            "department",
            "assigned_to",
            "assigned_by",
            "status",
            "-scheduled_at",
        ],
        "ordering": ["-scheduled_at"],
    }

    def __str__(self):
        return f"{self.title} - {self.assigned_to.full_name} - {self.scheduled_at.isoformat()}"

    def mark_acknowledged(self):
        self.status = "ACKNOWLEDGED"
        self.acknowledged_at = datetime.datetime.utcnow()

    def mark_completed(self):
        self.status = "COMPLETED"
        self.completed_at = datetime.datetime.utcnow()
