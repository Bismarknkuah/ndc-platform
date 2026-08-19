def can_manage_events(user, target_unit) -> bool:
    """
    Organizing a Campaign or Event for `target_unit` requires the
    "hierarchy.manage" permission and that the user's own unit is
    `target_unit` itself or an ancestor of it - the same ancestor-scoped
    delegation pattern used for broadcasts, meetings, and hierarchy
    management. A National officer can organize a national campaign or
    reach down to organize a single constituency's rally; a Constituency
    chairman can only organize within their own constituency.
    """
    if user.is_superadmin:
        return True
    if not (user.role and "hierarchy.manage" in (user.role.permissions or [])):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)
