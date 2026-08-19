import datetime

from mongoengine import DateTimeField, Document


class TimestampedDocument(Document):
    """Abstract base adding created_at / updated_at to every domain document."""

    meta = {"abstract": True}

    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)
