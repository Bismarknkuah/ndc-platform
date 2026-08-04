def can_manage_media(user, target_unit) -> bool:
    """Uploading/deleting media scoped to `target_unit` requires
    "hierarchy.manage", ancestor-scoped, same pattern as documents."""
    if user.is_superadmin:
        return True
    if not (user.role and "hierarchy.manage" in (user.role.permissions or [])):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)


def can_view_media(user, asset) -> bool:
    if user.is_superadmin or asset.is_public_within_party:
        return True
    if user.organizational_unit is None:
        return False
    return asset.organizational_unit.is_same_or_ancestor_of(
        user.organizational_unit
    ) or user.organizational_unit.is_same_or_ancestor_of(asset.organizational_unit)
