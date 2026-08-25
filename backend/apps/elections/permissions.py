ELECTION_DEPARTMENT_CODES = ("elections", "it")


def _department_election_authority(user, scope_unit) -> bool:
    """
    True if `user` holds HEAD/DEPUTY_HEAD of the Elections or IT
    department at `scope_unit` or an ancestor of it. This is what makes a
    Regional/Constituency ("district") IT director real without inventing
    a new Role per level: appoint them as HEAD of the Elections/IT
    department at their Region/Constituency via the existing department
    system (POST /api/v1/departments/assignments/), and this check gives
    them the exact same authority the National Election & IT Director has,
    just scoped to their own subtree - identical to how department
    meetings/tasks already cascade.
    """
    from apps.departments.documents import Department
    from apps.departments.permissions import has_department_authority

    departments = Department.objects(code__in=ELECTION_DEPARTMENT_CODES)
    for department in departments:
        if has_department_authority(user, department, scope_unit):
            return True
    return False


SECRETARY_ROLE_CODES = (
    "national_general_secretary",
    "regional_secretary",
    "constituency_secretary",
    "branch_secretary",
)


def can_view_election_progress(user, election) -> bool:
    """
    Live, in-progress results (before the election reaches COMPLETED) are
    only visible to people with a genuine reason to see them mid-process:
    whoever actually organizes the election (can_manage_election), plus -
    by explicit design - real transparency for the Chairman and the
    Secretary of the relevant level, even though neither organizes the
    election themselves. Chairman-level roles hold hierarchy.manage
    (general oversight); Secretary is checked by role code specifically
    since Secretary deliberately does not carry hierarchy.manage (see
    apps/dashboard/role_insights.py's SECRETARY_ROLE_CODES) - without this
    explicit carve-out, removing organizing authority from Chairman roles
    would have also silently removed their ability to watch an election
    they have every legitimate reason to watch.

    Once the election is COMPLETED, results are public to any
    authenticated member - see the status check at the call site in
    ResultSummaryView, not duplicated here.
    """
    if can_manage_election(user, election.scope_unit):
        return True

    unit = user.organizational_unit
    if unit is None:
        return False
    if not unit.is_same_or_ancestor_of(election.scope_unit):
        return False

    if user.role and "hierarchy.manage" in (user.role.permissions or []):
        return True
    if user.role and user.role.code in SECRETARY_ROLE_CODES:
        return True
    return False


def can_request_election(user, target_unit) -> bool:
    """
    Any real executive can request an election for their own unit -
    department can't organize one themselves (see can_manage_election
    above, centralized exclusively to the Election/IT Director), but
    every department and unit executive still needs a way to ask for
    one. Deliberately broad: hierarchy.manage (any Chairman-level
    executive) or being HEAD/DEPUTY_HEAD of any department at this unit
    (reusing has_any_department_authority, same as document/media
    upload authority) - a genuine executive, not an ordinary member
    submitting requests on a whim.
    """
    if user.is_superadmin:
        return True
    if user.role and "hierarchy.manage" in (user.role.permissions or []):
        if (
            user.organizational_unit
            and user.organizational_unit.is_same_or_ancestor_of(target_unit)
        ):
            return True

    from apps.departments.permissions import has_any_department_authority

    return has_any_department_authority(user, target_unit)


def can_manage_election(user, scope_unit) -> bool:
    """
    True if `user` may create/manage an Election (or its candidates,
    electorate, and result oversight) covering `scope_unit`. Two
    independent paths grant this:

    1. The "elections.manage" role permission plus ancestor-scoped
       authority (the National Election & IT Director role carries this).
    2. HEAD/DEPUTY_HEAD of the Elections or IT department at `scope_unit`
       or an ancestor of it (a Regional/Constituency-level IT director
       appointed through the department system).

    Together these mean "organize elections at all levels" is a single
    rule, not per-level special-casing - a national election, a regional
    party primary, or a district-level poll are all just different
    scope_unit values against the same check.
    """
    if user.is_superadmin:
        return True

    if user.role and "elections.manage" in (user.role.permissions or []):
        if (
            user.organizational_unit is not None
            and user.organizational_unit.is_same_or_ancestor_of(scope_unit)
        ):
            return True

    return _department_election_authority(user, scope_unit)


def can_manage_voters(user, election) -> bool:
    """Selecting the electorate for an election is part of organizing it."""
    return can_manage_election(user, election.scope_unit)


def can_submit_result(user, branch_unit) -> bool:
    """
    Submitting a branch's (polling station's) collation sheet now requires
    an explicit designation, not just "any executive at that branch" -
    "the district IT should assign one of the branch executives for all
    the branches in their jurisdiction to submit their results". That
    designation *is* an active DepartmentAssignment in the Elections/IT
    department at this specific branch, created by a district/regional/
    national IT director via the existing department-assignment endpoint
    (which already enforces that only someone with authority over this
    branch's chain can make that appointment).
    """
    if user.is_superadmin:
        return True

    from apps.departments.documents import Department, DepartmentAssignment

    departments = Department.objects(code__in=ELECTION_DEPARTMENT_CODES)
    return (
        DepartmentAssignment.objects(
            user=user,
            department__in=list(departments),
            organizational_unit=branch_unit,
            is_active=True,
        ).first()
        is not None
    )


def can_verify_result(user, branch_unit) -> bool:
    """The collation authority for a branch's result: elections.manage
    (role or department) holder whose unit is that branch or an ancestor of it."""
    return can_manage_election(user, branch_unit)


def is_eligible_voter(user, election) -> bool:
    from apps.elections.constants import MANDATORY_OPEN_ELECTORATE_TYPES
    from apps.elections.documents import EligibleVoter

    if election.election_type in MANDATORY_OPEN_ELECTORATE_TYPES:
        # Supreme Court ruling: every active member is eligible for a
        # presidential or parliamentary primary - no electorate
        # selection involved, and this is evaluated fresh every time,
        # not a frozen list, so a member who becomes active mid-election
        # is immediately eligible and one who becomes inactive
        # immediately is not.
        if not user.is_active:
            return False
        if election.election_type == "PARLIAMENTARY_PRIMARY":
            # Only members whose own unit is within the specific
            # constituency the primary is for (e.g. a Branch inside
            # it) - a National-level executive's own unit being an
            # ancestor of every constituency must not grant them a vote
            # in one they aren't actually a member of, so this check is
            # deliberately one-directional.
            if user.organizational_unit is None:
                return False
            return election.scope_unit.is_same_or_ancestor_of(user.organizational_unit)
        return True

    return EligibleVoter.objects(election=election, user=user).first() is not None
