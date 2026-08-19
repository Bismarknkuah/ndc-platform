def can_manage_campaign(user, target_unit) -> bool:
    """Organizing a fundraising campaign, or recording a pledge on someone
    else's behalf, requires "finance.manage" or "hierarchy.manage",
    ancestor-scoped - same OR pattern as welfare."""
    if user.is_superadmin:
        return True
    permissions = (user.role.permissions or []) if user.role else []
    if not ("finance.manage" in permissions or "hierarchy.manage" in permissions):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)
