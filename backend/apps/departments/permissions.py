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
