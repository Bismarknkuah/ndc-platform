from apps.departments.constants import AUTHORITY_POSITIONS
from apps.departments.documents import DepartmentAssignment


def get_authority_units(user, department):
    """
    Returns the list of OrganizationalUnits at which `user` holds a HEAD or
    DEPUTY_HEAD position in `department` - i.e. the roots of the subtrees
    they have management authority over.
    """
    assignments = DepartmentAssignment.objects(
        user=user,
        department=department,
        is_active=True,
        position__in=AUTHORITY_POSITIONS,
    )
    return [a.organizational_unit for a in assignments]


def has_any_department_authority(user, target_unit) -> bool:
    """
    True if `user` holds HEAD/DEPUTY_HEAD in *any* department at
    `target_unit` or an ancestor of it - not scoped to one specific
    department like has_department_authority above. Exists for actions
    where tracking which department an item belongs to isn't the point
    (uploading a document or media asset doesn't need a department
    field the way a departmental meeting does), but a real department
    head - Communications Director being the clearest case - genuinely
    should be able to act within their own unit without also needing
    the broader hierarchy.manage a Chairman carries.
    """
    if user.is_superadmin:
        return True
    assignments = DepartmentAssignment.objects(
        user=user, is_active=True, position__in=AUTHORITY_POSITIONS
    )
    for assignment in assignments:
        if assignment.organizational_unit.is_same_or_ancestor_of(target_unit):
            return True
    return False


def has_department_authority(user, department, target_unit) -> bool:
    """
    True if `user` may manage department assignments / assign tasks for
    `department` at `target_unit`. This is true if the user is a
    superadmin, or holds HEAD/DEPUTY_HEAD in that department at
    `target_unit` itself or at any ancestor of it.
    """
    if user.is_superadmin:
        return True
    for authority_unit in get_authority_units(user, department):
        if authority_unit.is_same_or_ancestor_of(target_unit):
            return True
    return False


def can_bootstrap_department_head(user) -> bool:
    """
    Appointing the very first HEAD of a department (e.g. the National
    Communications Director) can't rely on has_department_authority since
    no one holds that authority yet. National-level executives who can
    manage roles/hierarchy (e.g. the National Chairman/Secretary) are
    trusted to make that initial appointment.
    """
    if user.is_superadmin:
        return True
    return bool(user.role and "hierarchy.manage_roles" in (user.role.permissions or []))


def has_general_oversight(user, target_unit) -> bool:
    """
    True for someone with broad hierarchy authority over a unit
    (National Chairman, a Regional Chairman over their own region, etc.)
    even without a specific DepartmentAssignment in the department being
    viewed. Deliberately separate from has_department_authority: a
    department member should only see their own department's activity,
    but a real executive with jurisdiction-wide oversight authority
    should be able to see any department's activity within that
    jurisdiction, same "hierarchy.manage, ancestor-scoped" pattern used
    everywhere else in this codebase (see apps.analytics.permissions,
    apps.complaints.permissions, etc.) - not a department-specific rule.
    """
    if user.is_superadmin:
        return True
    if not (user.role and "hierarchy.manage" in (user.role.permissions or [])):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)
