from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.accounts.documents import User
from apps.departments.constants import (
    ENGAGEMENT_TYPE_CHOICES,
    POSITION_CHOICES,
    TASK_STATUS_CHOICES,
)
from apps.departments.documents import Department, DepartmentAssignment, TaskAssignment
from apps.hierarchy.documents import OrganizationalUnit


class DepartmentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=150)
    code = serializers.CharField(max_length=64)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(read_only=True)

    def validate_code(self, value):
        qs = Department.objects(code=value)
        if self.instance is not None:
            qs = qs.filter(id__ne=self.instance.id)
        if qs.first():
            raise serializers.ValidationError(
                "A department with this code already exists."
            )
        return value

    def create(self, validated_data):
        return Department.objects.create(**validated_data)

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "name": instance.name,
            "code": instance.code,
            "description": instance.description,
            "is_active": instance.is_active,
        }


class DepartmentAssignmentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField(write_only=True)
    department_id = serializers.CharField(write_only=True)
    organizational_unit_id = serializers.CharField(write_only=True)
    position = serializers.ChoiceField(choices=POSITION_CHOICES)
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_user_id(self, value):
        try:
            return User.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("User not found.") from exc

    def validate_department_id(self, value):
        try:
            return Department.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Department not found.") from exc

    def validate_organizational_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def create(self, validated_data):
        return DepartmentAssignment.objects.create(
            user=validated_data["user_id"],
            department=validated_data["department_id"],
            organizational_unit=validated_data["organizational_unit_id"],
            position=validated_data["position"],
            appointed_by=validated_data.get("appointed_by"),
        )

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "user": {
                "id": str(instance.user.id),
                "full_name": instance.user.full_name,
                "email": instance.user.email,
                "membership_id": instance.user.membership_id,
            },
            "department": {
                "id": str(instance.department.id),
                "name": instance.department.name,
                "code": instance.department.code,
            },
            "organizational_unit": {
                "id": str(instance.organizational_unit.id),
                "name": instance.organizational_unit.name,
                "unit_type": instance.organizational_unit.unit_type,
            },
            "position": instance.position,
            "appointed_by": (
                instance.appointed_by.full_name if instance.appointed_by else None
            ),
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat(),
        }


class TaskAssignmentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    department_id = serializers.CharField(write_only=True)
    assigned_to_id = serializers.CharField(write_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    engagement_type = serializers.ChoiceField(choices=ENGAGEMENT_TYPE_CHOICES)
    platform_name = serializers.CharField(
        required=False, allow_blank=True, max_length=150
    )
    location = serializers.CharField(required=False, allow_blank=True, max_length=200)
    scheduled_at = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=TASK_STATUS_CHOICES, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_department_id(self, value):
        try:
            return Department.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Department not found.") from exc

    def validate_assigned_to_id(self, value):
        try:
            return User.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("User not found.") from exc

    def create(self, validated_data):
        return TaskAssignment.objects.create(
            department=validated_data["department_id"],
            assigned_to=validated_data["assigned_to_id"],
            assigned_by=validated_data["assigned_by"],
            title=validated_data["title"],
            description=validated_data.get("description", ""),
            engagement_type=validated_data["engagement_type"],
            platform_name=validated_data.get("platform_name", ""),
            location=validated_data.get("location", ""),
            scheduled_at=validated_data["scheduled_at"],
        )

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "department": {
                "id": str(instance.department.id),
                "name": instance.department.name,
            },
            "assigned_to": {
                "id": str(instance.assigned_to.id),
                "full_name": instance.assigned_to.full_name,
            },
            "assigned_by": {
                "id": str(instance.assigned_by.id),
                "full_name": instance.assigned_by.full_name,
            },
            "title": instance.title,
            "description": instance.description,
            "engagement_type": instance.engagement_type,
            "platform_name": instance.platform_name,
            "location": instance.location,
            "scheduled_at": instance.scheduled_at.isoformat(),
            "status": instance.status,
            "acknowledged_at": (
                instance.acknowledged_at.isoformat()
                if instance.acknowledged_at
                else None
            ),
            "completed_at": (
                instance.completed_at.isoformat() if instance.completed_at else None
            ),
            "created_at": instance.created_at.isoformat(),
        }
