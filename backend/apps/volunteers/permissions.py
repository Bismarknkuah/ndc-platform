def can_manage_opportunities(user, target_unit) -> bool:
    """Organizing a volunteer opportunity for `target_unit` requires
    "hierarchy.manage", ancestor-scoped - same as events."""
    if user.is_superadmin:
        return True
    if not (user.role and "hierarchy.manage" in (user.role.permissions or [])):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)
