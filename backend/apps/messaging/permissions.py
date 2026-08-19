def can_issue_broadcast(user, target_unit) -> bool:
    """
    A user may issue a broadcast (directive/announcement) to `target_unit`'s
    subtree if they carry the "messaging.broadcast.downward" permission and
    their own unit is `target_unit` itself or an ancestor of it - i.e. they
    are broadcasting down their own chain of command, not sideways or up.
    """
    if user.is_superadmin:
        return True
    if not (
        user.role and "messaging.broadcast.downward" in (user.role.permissions or [])
    ):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)


def can_submit_report(user) -> bool:
    if user.is_superadmin:
        return True
    return bool(
        user.role and "messaging.report.upward" in (user.role.permissions or [])
    )


def can_manage_report(user, report) -> bool:
    """
    The report's target office (or anyone above it) may acknowledge/resolve
    it - mirrors the same "unit or ancestor" authority pattern used
    throughout the platform.
    """
    if user.is_superadmin:
        return True
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(report.target_unit)


def _has_jurisdiction_authority(user, target_unit) -> bool:
    """
    True if `user` holds general "convene things in my own turf" authority
    over `target_unit` - their own unit is `target_unit` itself or an
    ancestor of it, and their role carries either the dedicated
    "meetings.call" permission or the broader "hierarchy.manage"
    permission (every hierarchy.manage holder already gets this for free;
    "meetings.call" exists for roles - e.g. a District/Constituency
    Secretary - that should be able to convene meetings without also
    getting hierarchy.manage's organizational-structure/member-provisioning
    powers).
    """
    permissions = (user.role.permissions or []) if user.role else []
    if not ("meetings.call" in permissions or "hierarchy.manage" in permissions):
        return False
    if user.organizational_unit is None:
        return False
    return user.organizational_unit.is_same_or_ancestor_of(target_unit)


def can_call_meeting(user, target_unit, department=None) -> bool:
    """
    Governs who may schedule a meeting/workshop for `target_unit`'s
    audience:

    - Department meetings ("the National/Regional/District Communications
      team meeting") are callable by anyone with department authority over
      that unit (a department HEAD/DEPUTY_HEAD - "all regional heads can
      call departmental meetings"; authority cascades down the tree just
      like team/task management, so "national can call regional or
      district"), OR by a general jurisdiction executive - a
      Chairman/Secretary - convening a department's meeting within their
      own turf even though they don't personally hold that department
      role ("district executive can call for departmental meetings under
      their jurisdiction").
    - General, non-departmental meetings require jurisdiction authority
      (see _has_jurisdiction_authority) - e.g. a Regional or District
      Chairman/Secretary calling a general meeting under their own
      jurisdiction.
    - Calling a meeting for the *entire party* (target_unit is the
      National root) requires the dedicated "meetings.call_all_members"
      permission specifically, reserved for the National Chairman /
      General Secretary ("the party leader or chairman or secretary can
      call for all members") - jurisdiction authority alone is not enough
      for this one case.
    """
    if user.is_superadmin:
        return True

    if department is not None:
        from apps.departments.permissions import has_department_authority

        return has_department_authority(
            user, department, target_unit
        ) or _has_jurisdiction_authority(user, target_unit)

    if target_unit.unit_type == "NATIONAL" and target_unit.parent is None:
        return bool(
            user.role and "meetings.call_all_members" in (user.role.permissions or [])
        )

    return _has_jurisdiction_authority(user, target_unit)
