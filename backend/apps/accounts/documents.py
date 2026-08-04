import datetime

from django.contrib.auth.hashers import check_password, make_password
from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    EmailField,
    ListField,
    ReferenceField,
    StringField,
)

from apps.core.documents import TimestampedDocument
from apps.hierarchy.constants import UNIT_TYPE_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


class Role(TimestampedDocument):
    name = StringField(required=True, max_length=150)
    code = StringField(required=True, unique=True, max_length=100)
    scope = StringField(
        required=True,
        choices=UNIT_TYPE_CHOICES,
        help_text="Which organizational unit type this role is held at.",
    )
    is_executive = BooleanField(default=True)
    is_active = BooleanField(default=True)
    permissions = ListField(StringField(), default=list)
    reports_to = ReferenceField("self", null=True, default=None)
    dashboard_config = DictField(default=dict)

    meta = {
        "collection": "roles",
        "indexes": ["scope", "is_active", {"fields": ["code"], "unique": True}],
        "ordering": ["scope", "name"],
    }

    def __str__(self):
        return self.name


class User(TimestampedDocument):
    GENDER_CHOICES = [("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other")]

    MARITAL_STATUS_CHOICES = [
        ("SINGLE", "Single"),
        ("MARRIED", "Married"),
        ("DIVORCED", "Divorced"),
        ("WIDOWED", "Widowed"),
        ("OTHER", "Other"),
    ]

    email = EmailField(required=True, unique=True)
    phone_number = StringField(required=True, unique=True, max_length=20)
    password_hash = StringField(required=True)

    first_name = StringField(required=True, max_length=100)
    last_name = StringField(required=True, max_length=100)
    membership_id = StringField(required=True, unique=True, max_length=32)

    national_id_number = StringField(null=True, max_length=64)
    voter_id_number = StringField(null=True, max_length=32)

    date_of_birth = DateTimeField(null=True)
    gender = StringField(choices=GENDER_CHOICES, null=True)

    residential_address = StringField(null=True, max_length=255)
    occupation = StringField(null=True, max_length=150)

    marital_status = StringField(choices=MARITAL_STATUS_CHOICES, null=True)

    emergency_contact_name = StringField(null=True, max_length=150)
    emergency_contact_phone = StringField(null=True, max_length=20)

    photo_base64 = StringField(null=True)
    photo_content_type = StringField(null=True, max_length=50)

    organizational_unit = ReferenceField(OrganizationalUnit, required=True)

    role = ReferenceField(Role, required=True)

    is_active = BooleanField(default=True)

    is_superadmin = BooleanField(default=False)

    must_change_password = BooleanField(default=False)

    last_login = DateTimeField(null=True)

    date_joined = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "users",
        "strict": False,
        "indexes": [
            {"fields": ["email"], "unique": True},
            {"fields": ["phone_number"], "unique": True},
            {"fields": ["membership_id"], "unique": True},
            {
                "fields": ["national_id_number"],
                "unique": True,
                "partialFilterExpression": {"national_id_number": {"$type": "string"}},
            },
            {
                "fields": ["voter_id_number"],
                "unique": True,
                "partialFilterExpression": {"voter_id_number": {"$type": "string"}},
            },
            "organizational_unit",
            "role",
        ],
        "ordering": ["last_name", "first_name"],
    }

    def set_password(self, raw_password: str):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password_hash)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def has_permission(self, permission_code: str) -> bool:
        return self.is_superadmin or permission_code in (
            self.role.permissions if self.role else []
        )

    def __str__(self):
        return f"{self.full_name} <{self.email}>"


class AnonymousUser:
    id = None
    is_superadmin = False
    role = None
    organizational_unit = None

    @property
    def is_authenticated(self):
        return False

    @property
    def is_anonymous(self):
        return True
