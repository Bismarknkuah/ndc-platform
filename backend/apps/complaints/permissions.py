def can_manage_complaint(user, target_unit) -> bool:
    """
    The complaint's target office (or an office above it) may triage,
    assign, and resolve it - same ancestor-scoped pattern as report
    management, gated on "hierarchy.manage".
    """
    if user.is_superadmin:
        return True
    if not (user.role and "hierarchy.manage" in (user.role.permissions or [])):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)


def can_view_complaint(user, complaint) -> bool:
    if user.is_superadmin or complaint.submitted_by.id == user.id:
        return True
    if complaint.assigned_to and complaint.assigned_to.id == user.id:
        return True
    return can_manage_complaint(user, complaint.target_unit)
