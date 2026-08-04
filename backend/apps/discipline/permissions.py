def can_manage_discipline(user, target_unit) -> bool:
    """
    The Executive Committee at `target_unit` (or any ancestor of it) has
    authority over the Disciplinary Committee roster, case decisions, and
    precautionary suspensions at that unit - same ancestor-scoped
    "hierarchy.manage" pattern used throughout the platform (Complaints,
    Hierarchy management, etc).
    """
    if user.is_superadmin:
        return True
    if not (user.role and "hierarchy.manage" in (user.role.permissions or [])):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)


def is_committee_member(user, committee) -> bool:
    if user.is_superadmin:
        return True
    if committee is None:
        return False
    return any(str(member.id) == str(user.id) for member in committee.members)


def can_deliberate_case(user, case) -> bool:
    """Only the assigned Disciplinary Committee's own members may convene,
    deliberate, and record a recommendation - Article 46(8): "A
    Disciplinary Committee shall not be subject to the control or
    direction of any person in the performance of its functions.\" """
    if user.is_superadmin:
        return True
    return is_committee_member(user, case.committee)


def can_view_case(user, case) -> bool:
    if user.is_superadmin:
        return True
    if str(case.respondent.id) == str(user.id) or str(case.reported_by.id) == str(
        user.id
    ):
        return True
    if is_committee_member(user, case.committee):
        return True
    return can_manage_discipline(user, case.organizational_unit)
