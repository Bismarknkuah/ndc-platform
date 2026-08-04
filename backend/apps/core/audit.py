import datetime

from mongoengine import DateTimeField, DictField, Document, StringField


class AuditLog(Document):
    """
    Immutable record of a meaningful action taken in the system. Every
    module (auth, hierarchy, membership, messaging, finance, elections...)
    writes here via log_action() rather than each maintaining its own log,
    so a National Executive can pull one unified audit trail.
    """

    actor_id = StringField(required=True)
    actor_email = StringField()
    actor_role = StringField()
    actor_unit_id = StringField(null=True)

    action = StringField(required=True)  # e.g. "user.login", "hierarchy.unit.create"
    target_type = StringField(null=True)  # e.g. "OrganizationalUnit"
    target_id = StringField(null=True)

    description = StringField(default="")
    metadata = DictField(default=dict)

    ip_address = StringField(null=True)
    request_id = StringField(null=True)

    created_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "audit_logs",
        "indexes": [
            "actor_id",
            "action",
            ("target_type", "target_id"),
            "-created_at",
        ],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"{self.action} by {self.actor_email} at {self.created_at.isoformat()}"


def log_action(user, action, request=None, target=None, description="", metadata=None):
    """
    Write one AuditLog entry.

    user: the acting User document (or None for system actions)
    action: dotted action string, e.g. "hierarchy.unit.create"
    request: the DRF request object, if available (for IP / request_id)
    target: the affected document, if any (its class name and id are captured)
    """
    entry = AuditLog(
        actor_id=str(user.id) if user else "system",
        actor_email=getattr(user, "email", "system"),
        actor_role=(user.role.code if getattr(user, "role", None) else ""),
        actor_unit_id=(
            str(user.organizational_unit.id)
            if getattr(user, "organizational_unit", None)
            else None
        ),
        action=action,
        target_type=target.__class__.__name__ if target is not None else None,
        target_id=str(target.id) if target is not None else None,
        description=description,
        metadata=metadata or {},
        ip_address=getattr(request, "client_ip", None) if request else None,
        request_id=getattr(request, "request_id", None) if request else None,
    )
    entry.save()
    return entry
