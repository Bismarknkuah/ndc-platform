def can_manage_welfare(user, target_unit) -> bool:
    """
    Reviewing/approving a welfare request at `target_unit` requires either
    "finance.manage" or "hierarchy.manage" (welfare payouts are ultimately
    a finance decision, but general hierarchy authority covers it too),
    ancestor-scoped the same way as everywhere else.
    """
    if user.is_superadmin:
        return True
    permissions = (user.role.permissions or []) if user.role else []
    if not ("finance.manage" in permissions or "hierarchy.manage" in permissions):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)
