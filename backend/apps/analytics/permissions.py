def can_view_analytics(user, target_unit) -> bool:
    """Analytics can surface sensitive aggregates (gender breakdowns,
    finance-adjacent counts), so it follows the same "hierarchy.manage,
    ancestor-scoped" authority as everywhere else rather than being open
    to every member."""
    if user.is_superadmin:
        return True
    if not (user.role and "hierarchy.manage" in (user.role.permissions or [])):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)
