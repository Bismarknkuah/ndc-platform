from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.hierarchy.constants import UNIT_TYPE_CHOICES, expected_parent_type
from apps.hierarchy.documents import OrganizationalUnit


class OrganizationalUnitSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=200)
    code = serializers.CharField(max_length=64)
    unit_type = serializers.ChoiceField(choices=UNIT_TYPE_CHOICES)
    parent_id = serializers.CharField(required=False, allow_null=True, source="parent")
    metadata = serializers.DictField(required=False)
    latitude = serializers.FloatField(
        required=False, allow_null=True, min_value=-90, max_value=90
    )
    longitude = serializers.FloatField(
        required=False, allow_null=True, min_value=-180, max_value=180
    )
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def validate_code(self, value):
        qs = OrganizationalUnit.objects(code=value)
        if self.instance is not None:
            qs = qs.filter(id__ne=self.instance.id)
        if qs.first():
            raise serializers.ValidationError(
                "An organizational unit with this code already exists."
            )
        return value

    def validate(self, attrs):
        unit_type = attrs.get("unit_type", getattr(self.instance, "unit_type", None))

        # On a partial update (PATCH), "parent" only appears in attrs if
        # the caller actually sent parent_id. Re-validating parentage on
        # every PATCH - even ones only touching e.g. latitude/longitude -
        # would incorrectly demand parent_id again on every edit.
        parent_being_set = "parent" in attrs
        creating_new_unit = self.instance is None

        if parent_being_set or creating_new_unit:
            parent_id = attrs.get("parent")
            parent = None
            if parent_id:
                try:
                    parent = OrganizationalUnit.objects.get(
                        id=parent_id, is_active=True
                    )
                except (DoesNotExist, MongoValidationError) as exc:
                    raise serializers.ValidationError(
                        {"parent_id": "Parent unit not found."}
                    ) from exc

            required_parent_type = expected_parent_type(unit_type)
            if required_parent_type is not None:
                if parent is None:
                    raise serializers.ValidationError(
                        {
                            "parent_id": f"A {unit_type} unit requires a {required_parent_type} parent."
                        }
                    )
                if parent.unit_type != required_parent_type:
                    message = (
                        f"A {unit_type} unit's parent must be of type "
                        f"{required_parent_type}, got {parent.unit_type}."
                    )
                    raise serializers.ValidationError({"parent_id": message})
            attrs["parent"] = parent

        lat = attrs.get("latitude", getattr(self.instance, "latitude", None))
        lng = attrs.get("longitude", getattr(self.instance, "longitude", None))
        if (lat is None) != (lng is None):
            raise serializers.ValidationError(
                {
                    "latitude": "latitude and longitude must be set together, or both left unset."
                }
            )
        return attrs

    def create(self, validated_data):
        return OrganizationalUnit.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        data = {
            "id": str(instance.id),
            "name": instance.name,
            "code": instance.code,
            "unit_type": instance.unit_type,
            "parent_id": str(instance.parent.id) if instance.parent else None,
            "parent_name": instance.parent.name if instance.parent else None,
            "metadata": instance.metadata,
            "latitude": instance.latitude,
            "longitude": instance.longitude,
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
        }
        return data
