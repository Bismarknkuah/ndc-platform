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
    """The top tier: party-wide Ground Intelligence over any unit in the
    system, not just the caller's own jurisdiction. Deliberately narrow -
    Flagbearer, National Chairman, National General Secretary - since
    seeing real complaint/welfare/report text from a part of the party
    you have no actual authority over is a materially broader, more
    sensitive capability than the jurisdiction rollup every executive
    already gets for their own unit."""
    if user.is_superadmin:
        return True
    return bool(
        user.role and "analytics.ground_intelligence" in (user.role.permissions or [])
    )


def can_access_ground_intelligence_for_unit(user, target_unit) -> bool:
    """The scoped tier: any real executive (hierarchy.manage) can use
    Ground Intelligence and the AI leadership tools too, but only for a
    unit within their own jurisdiction - their own unit or a descendant
    of it, same ancestor-scoped rule used everywhere else in this
    codebase. A Regional Chairman gets real ground intelligence for
    their own region; they do not get it for a region they have no
    authority over. The top tier above always passes this check too,
    for any unit whatsoever."""
    if can_view_ground_intelligence(user):
        return True
    if not (user.role and "hierarchy.manage" in (user.role.permissions or [])):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)
