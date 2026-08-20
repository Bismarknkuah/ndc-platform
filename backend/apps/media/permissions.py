def _department_media_authority(user, target_unit) -> bool:
    """
    True if `user` holds HEAD/DEPUTY_HEAD of the Communications
    department at `target_unit` or an ancestor of it - same pattern as
    apps.elections.permissions._department_election_authority. Media
    (photos, videos, audio, press clippings) is squarely the
    Communications department's actual job, and without this a
    Communications Director could not upload the very thing they exist
    to manage, since the role itself deliberately carries only
    messaging.broadcast.downward, not hierarchy.manage.
    """
    from apps.departments.documents import Department
    from apps.departments.permissions import has_department_authority

    department = Department.objects(code="communications").first()
    if department is None:
        return False
    return has_department_authority(user, department, target_unit)


def can_manage_media(user, target_unit) -> bool:
    """
    Uploading/deleting media scoped to `target_unit` is granted by
    either of two independent paths:

    1. "hierarchy.manage", ancestor-scoped - general executive oversight,
       same as documents.
    2. HEAD/DEPUTY_HEAD of the Communications department at `target_unit`
       or an ancestor of it - the department this actually belongs to.
    """
    if user.is_superadmin:
        return True
    if user.role and "hierarchy.manage" in (user.role.permissions or []):
        if (
            user.organizational_unit is not None
            and user.organizational_unit.is_same_or_ancestor_of(target_unit)
        ):
            return True
    return _department_media_authority(user, target_unit)


def can_view_media(user, asset) -> bool:
    if user.is_superadmin or asset.is_public_within_party:
        return True
    if user.organizational_unit is None:
        return False
    return asset.organizational_unit.is_same_or_ancestor_of(
        user.organizational_unit
    ) or user.organizational_unit.is_same_or_ancestor_of(asset.organizational_unit)
