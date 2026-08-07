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


def can_view_ground_intelligence(user) -> bool:
    """Ground Intelligence pulls together real complaint, welfare, and
    report text from across any part of the party the caller selects -
    a materially broader, more sensitive view than the jurisdiction
    rollup every executive already gets for their own unit. Gated on a
    specific permission (analytics.ground_intelligence) rather than the
    general hierarchy.manage check, so this stays limited to the roles
    that actually need it (Flagbearer, National Chairman) rather than
    every executive at every level."""
    if user.is_superadmin:
        return True
    return bool(
        user.role and "analytics.ground_intelligence" in (user.role.permissions or [])
    )
