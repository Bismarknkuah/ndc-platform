def can_manage_finance(user, target_unit) -> bool:
    """
    Recording or reviewing a finance entry at `target_unit` requires the
    "finance.manage" permission and that the user's own unit is
    `target_unit` itself or an ancestor of it - the same ancestor-scoped
    delegation pattern used throughout. The National Treasurer role
    already carries "finance.manage"; a Regional/Constituency treasurer
    would carry the same permission scoped to their own unit.
    """
    if user.is_superadmin:
        return True
    if not (user.role and "finance.manage" in (user.role.permissions or [])):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)


def can_view_finance(user, target_unit) -> bool:
    """finance.view (read-only) or finance.manage, ancestor-scoped."""
    if user.is_superadmin:
        return True
    permissions = (user.role.permissions or []) if user.role else []
    if not ("finance.manage" in permissions or "finance.view" in permissions):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)
