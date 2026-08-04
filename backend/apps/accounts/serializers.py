from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.accounts.documents import Role, User
from apps.hierarchy.constants import UNIT_TYPE_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


def generate_membership_id(unit: OrganizationalUnit) -> str:
    import random
    import string

    prefix = "NDC"
    unit_code = (unit.code or "GEN")[:4].upper()
    while True:
        suffix = "".join(random.choices(string.digits, k=6))
        candidate = f"{prefix}-{unit_code}-{suffix}"
        if not User.objects(membership_id=candidate).first():
            return candidate


def get_or_create_ordinary_role() -> Role:
    role = Role.objects(code="ordinary_member").first()
    if role is None:
        role = Role.objects.create(
            code="ordinary_member",
            name="Ordinary Member",
            scope="BRANCH",
            is_executive=False,
            permissions=["profile.manage_own"],
        )
    return role


class RoleReportsToSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    code = serializers.CharField()


class RoleSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    code = serializers.CharField()
    scope = serializers.CharField()
    is_executive = serializers.BooleanField()
    is_active = serializers.BooleanField(read_only=True)
    permissions = serializers.ListField(child=serializers.CharField())
    dashboard_config = serializers.DictField(read_only=True)
    reports_to = serializers.SerializerMethodField()

    @extend_schema_field(RoleReportsToSerializer)
    def get_reports_to(self, obj):
        if not obj.reports_to:
            return None
        return {
            "id": str(obj.reports_to.id),
            "name": obj.reports_to.name,
            "code": obj.reports_to.code,
        }


class RoleWriteSerializer(serializers.Serializer):
    """
    Backs the Position Management Module: create a new position, rename
    one, add/remove a deputy position, redefine its reporting line, or
    amend its permissions - all without a code deployment. Restricted to
    holders of "hierarchy.manage_roles" (see apps.accounts.views.
    RoleListCreateView / RoleDetailView).
    """

    name = serializers.CharField(max_length=150, required=False)
    code = serializers.CharField(max_length=100, required=False)
    scope = serializers.ChoiceField(choices=UNIT_TYPE_CHOICES, required=False)
    is_executive = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    permissions = serializers.ListField(child=serializers.CharField(), required=False)
    reports_to_id = serializers.CharField(required=False, allow_null=True)
    dashboard_config = serializers.DictField(required=False)

    def validate_code(self, value):
        qs = Role.objects(code=value)
        if self.instance is not None:
            qs = qs.filter(id__ne=self.instance.id)
        if qs.first():
            raise serializers.ValidationError(
                "A position with this code already exists."
            )
        return value

    def validate_reports_to_id(self, value):
        if not value:
            return None
        try:
            reports_to = Role.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Reports-to position not found.") from exc
        if self.instance is not None:
            if reports_to.id == self.instance.id:
                raise serializers.ValidationError("A position cannot report to itself.")
            # Walk the proposed chain upward looking for the role being
            # edited - catches longer cycles (A -> B -> A), not just the
            # direct self-reference checked above.
            seen = set()
            current = reports_to
            while current is not None and current.reports_to is not None:
                if current.id in seen:
                    break  # an unrelated pre-existing cycle - not this edit's problem to fix
                seen.add(current.id)
                current = current.reports_to
                if current is not None and current.id == self.instance.id:
                    raise serializers.ValidationError(
                        "This would create a circular reporting chain."
                    )
        return reports_to


class OrganizationalUnitSummarySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    code = serializers.CharField()
    unit_type = serializers.CharField()


class UserSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.CharField(read_only=True)
    membership_id = serializers.CharField(read_only=True)
    national_id_number = serializers.CharField(required=False, allow_null=True)
    voter_id_number = serializers.CharField(required=False, allow_null=True)
    date_of_birth = serializers.DateTimeField(required=False, allow_null=True)
    gender = serializers.CharField(required=False, allow_null=True)
    residential_address = serializers.CharField(required=False, allow_null=True)
    occupation = serializers.CharField(required=False, allow_null=True)
    marital_status = serializers.CharField(required=False, allow_null=True)
    emergency_contact_name = serializers.CharField(required=False, allow_null=True)
    emergency_contact_phone = serializers.CharField(required=False, allow_null=True)
    must_change_password = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_superadmin = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True, allow_null=True)
    role = serializers.SerializerMethodField()
    organizational_unit = serializers.SerializerMethodField()
    has_photo = serializers.SerializerMethodField()
    photo_base64 = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    photo_content_type = serializers.CharField(required=False, allow_null=True)

    @extend_schema_field(RoleSerializer)
    def get_role(self, obj):
        return RoleSerializer(obj.role).data if obj.role else None

    @extend_schema_field(OrganizationalUnitSummarySerializer)
    def get_organizational_unit(self, obj):
        return (
            OrganizationalUnitSummarySerializer(obj.organizational_unit).data
            if obj.organizational_unit
            else None
        )

    @extend_schema_field(serializers.BooleanField)
    def get_has_photo(self, obj):
        return bool(obj.photo_base64)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Strip the actual base64 payload from list views (paginated
        # member lists) - same reasoning as PartyDocument/MediaAsset:
        # embedding full images in every row of a list response is a
        # real N+1-style bloat problem. `has_photo` (cheap, boolean)
        # is always present so the UI knows whether to show a fetch
        # link; the real bytes are only ever included when this
        # serializer is used for a single user (context flag set by
        # the paginated list view specifically, not by default).
        if self.context.get("list_view"):
            data.pop("photo_base64", None)
        return data


class RegisterSerializer(serializers.Serializer):
    """
    Self-service registration for an Ordinary Member at a Branch. Executive
    role assignment is a privileged action performed separately by an
    authorized officer (see AssignRoleView), never at signup.
    """

    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    gender = serializers.ChoiceField(
        choices=["MALE", "FEMALE", "OTHER"], required=False
    )
    national_id_number = serializers.CharField(
        max_length=64, required=False, allow_blank=True
    )
    voter_id_number = serializers.CharField(
        max_length=32, required=False, allow_blank=True
    )
    date_of_birth = serializers.DateTimeField(required=False)
    residential_address = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    occupation = serializers.CharField(max_length=150, required=False, allow_blank=True)
    marital_status = serializers.ChoiceField(
        choices=["SINGLE", "MARRIED", "DIVORCED", "WIDOWED", "OTHER"], required=False
    )
    emergency_contact_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    emergency_contact_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    organizational_unit_id = serializers.CharField()

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate_email(self, value):
        if User.objects(email=value).first():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_number(self, value):
        if User.objects(phone_number=value).first():
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )
        return value

    def validate_national_id_number(self, value):
        if value and User.objects(national_id_number=value).first():
            raise serializers.ValidationError(
                "A user with this national ID number already exists."
            )
        return value

    def validate_voter_id_number(self, value):
        if value and User.objects(voter_id_number=value).first():
            raise serializers.ValidationError(
                "A user with this voter ID number already exists."
            )
        return value

    def validate_organizational_unit_id(self, value):
        try:
            unit = OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc
        return unit

    def create(self, validated_data):
        ordinary_role = get_or_create_ordinary_role()
        unit = validated_data["organizational_unit_id"]
        user = User(
            email=validated_data["email"],
            phone_number=validated_data["phone_number"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            gender=validated_data.get("gender"),
            date_of_birth=validated_data.get("date_of_birth"),
            residential_address=validated_data.get("residential_address", ""),
            occupation=validated_data.get("occupation", ""),
            marital_status=validated_data.get("marital_status"),
            emergency_contact_name=validated_data.get("emergency_contact_name", ""),
            emergency_contact_phone=validated_data.get("emergency_contact_phone", ""),
            organizational_unit=unit,
            role=ordinary_role,
            membership_id=generate_membership_id(unit),
        )
        # national_id_number / voter_id_number are sparse-uniquely indexed:
        # only set them when a real value is supplied, otherwise multiple
        # blank registrations would collide with each other as duplicates.
        if validated_data.get("national_id_number"):
            user.national_id_number = validated_data["national_id_number"]
        if validated_data.get("voter_id_number"):
            user.voter_id_number = validated_data["voter_id_number"]
        user.set_password(validated_data["password"])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AdminCreateMemberSerializer(serializers.Serializer):
    """
    Used by an executive (e.g. a Constituency/"district" chairman, or a
    Branch Chairman/Secretary registering voters/members in their own
    branch) to directly provision a member account on someone else's
    behalf, rather than the member self-registering. Because this is an
    assisted, in-person registration, more data is required than the
    self-service flow so the party's membership/voter records are
    actually complete - not just a name and phone number. A random
    temporary password is generated and returned once in the response;
    the account is flagged must_change_password so the frontend can force
    a reset on first login.
    """

    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    gender = serializers.ChoiceField(choices=["MALE", "FEMALE", "OTHER"])
    date_of_birth = serializers.DateTimeField()
    national_id_number = serializers.CharField(max_length=64)
    voter_id_number = serializers.CharField(
        max_length=32, required=False, allow_blank=True
    )
    residential_address = serializers.CharField(max_length=255)
    emergency_contact_name = serializers.CharField(max_length=150)
    emergency_contact_phone = serializers.CharField(max_length=20)
    occupation = serializers.CharField(max_length=150, required=False, allow_blank=True)
    marital_status = serializers.ChoiceField(
        choices=["SINGLE", "MARRIED", "DIVORCED", "WIDOWED", "OTHER"], required=False
    )
    organizational_unit_id = serializers.CharField()
    role_id = serializers.CharField(required=False, allow_null=True)

    # Optional: also place the new member into a department in the same call.
    department_id = serializers.CharField(required=False, allow_null=True)
    department_position = serializers.ChoiceField(
        choices=["HEAD", "DEPUTY_HEAD", "OFFICER", "MEMBER"],
        required=False,
        allow_null=True,
    )

    def validate_email(self, value):
        if User.objects(email=value).first():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_number(self, value):
        if User.objects(phone_number=value).first():
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )
        return value

    def validate_national_id_number(self, value):
        if User.objects(national_id_number=value).first():
            raise serializers.ValidationError(
                "A user with this national ID number already exists."
            )
        return value

    def validate_voter_id_number(self, value):
        if value and User.objects(voter_id_number=value).first():
            raise serializers.ValidationError(
                "A user with this voter ID number already exists."
            )
        return value

    def validate_organizational_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def validate_role_id(self, value):
        if not value:
            return None
        try:
            return Role.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Role not found.") from exc

    def validate(self, attrs):
        if attrs.get("department_id") and not attrs.get("department_position"):
            raise serializers.ValidationError(
                {"department_position": "Required when department_id is supplied."}
            )
        return attrs


class AssignRoleSerializer(serializers.Serializer):
    """Privileged action: appoint or change a member's executive role."""

    user_id = serializers.CharField()
    role_id = serializers.CharField()

    def validate_user_id(self, value):
        try:
            return User.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("User not found.") from exc

    def validate_role_id(self, value):
        try:
            return Role.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Role not found.") from exc


class MemberAdminUpdateSerializer(serializers.Serializer):
    """Suspend/reactivate a member, or correct their basic profile data,
    as an executive with authority over their unit - see
    apps.accounts.views.MemberDetailView."""

    is_active = serializers.BooleanField(required=False)
    deactivation_reason = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    national_id_number = serializers.CharField(
        max_length=64, required=False, allow_blank=True
    )
    voter_id_number = serializers.CharField(
        max_length=32, required=False, allow_blank=True
    )


class MemberTransferSerializer(serializers.Serializer):
    """Moves a member to a different Branch/unit - see
    apps.accounts.views.MemberTransferView."""

    target_organizational_unit_id = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate_target_organizational_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError(
                "Target organizational unit not found."
            ) from exc
