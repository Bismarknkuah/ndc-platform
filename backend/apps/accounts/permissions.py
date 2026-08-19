from rest_framework.permissions import BasePermission

from apps.hierarchy.constants import MAIN_CHAIN_RANK


class HasRolePermission(BasePermission):
    """
    Generic permission: grants access if the authenticated user's role
    carries the given permission code, or if they are a superadmin.
    Usage: HasRolePermission.requiring("hierarchy.manage")
    """

    permission_code = None

    def has_permission(self, request, view):
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False
        return user.has_permission(self.permission_code)

    @classmethod
    def requiring(cls, permission_code: str):
        return type(
            f"HasRolePermission_{permission_code.replace('.', '_')}",
            (cls,),
            {"permission_code": permission_code},
        )


class IsNationalOfficer(BasePermission):
    """Grants access only to executives whose role scope is NATIONAL (or superadmins)."""

    def has_permission(self, request, view):
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False
        if user.is_superadmin:
            return True
        return bool(user.role and user.role.scope == "NATIONAL")


class IsAtOrAboveUnitRank(BasePermission):
    """
    Grants access if the requesting user's organizational unit is the same
    as, or a main-chain ancestor of, the unit referenced by the view
    (view must set `get_target_unit(request)` returning an OrganizationalUnit).
    Falls back to True for superadmins.
    """

    def has_object_permission(self, request, view, obj_unit):
        user = request.user
        if user.is_superadmin:
            return True
        user_unit = user.organizational_unit
        if user_unit is None:
            return False
        return user_unit.is_same_or_ancestor_of(obj_unit)


def rank_of(unit_type: str):
    """Convenience accessor used by views doing manual rank comparisons."""
    return MAIN_CHAIN_RANK.get(unit_type)


def can_manage_members_at(user, target_unit) -> bool:
    """
    True if `user` may create/manage member accounts at `target_unit` -
    e.g. a Constituency/"district" executive entering Branch executives for
    every branch under their constituency, or a Branch Chairman/Secretary
    registering voters/party members within their own branch. Requires
    that the acting user's own unit is `target_unit` itself or an ancestor
    of it (the same ancestor-scoped delegation pattern used for
    departments, broadcasts, and meetings), *and* their role carries
    either "hierarchy.manage" (which already implies member management) or
    the narrower "membership.register" permission. The latter exists for
    roles - like Branch Chairman/Secretary - that should be able to
    register members in their own jurisdiction without also gaining
    "hierarchy.manage"'s power to create/edit/delete organizational units.
    """
    if user.is_superadmin:
        return True
    permissions = (user.role.permissions or []) if user.role else []
    if not ("hierarchy.manage" in permissions or "membership.register" in permissions):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)


def can_manage_roles(user) -> bool:
    """
    True if `user` may manage the global Role catalog (the Position
    Management Module: create/rename/retire positions, redefine
    reporting lines, amend permissions). Deliberately stricter than the
    generic "hierarchy.manage_roles" permission check used for
    *assigning* an existing role to a member (see AssignRoleView): Role
    documents are global, not scoped to an organizational unit, so a
    Regional or Constituency officer who happens to hold
    "hierarchy.manage_roles" must NOT be able to edit or retire a
    National-level position - editing the position catalog itself is
    reserved for National-level authority (e.g. the General Secretary or
    National IT Director), matching how the party constitution actually
    works. Without this extra check, a National Chairman could
    inadvertently grant a newly-created Regional position enough power to
    edit National positions, which this closes off.
    """
    if user.is_superadmin:
        return True
    if user.role is None or "hierarchy.manage_roles" not in (
        user.role.permissions or []
    ):
        return False
    return bool(
        user.organizational_unit and user.organizational_unit.unit_type == "NATIONAL"
    )
