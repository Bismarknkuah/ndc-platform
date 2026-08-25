"""
Real, role-specific dashboard content for officers who are neither a
department head (see department_insights.py) nor a broad
jurisdiction-oversight executive (who already gets the full
jurisdiction rollup) - specifically the Secretary track (National,
Regional, Constituency, Branch) and the Youth/Women Wing organizers.
These roles are deliberately narrow (see seed_platform.py's BASE_ROLES:
Secretary is the administrative engine, not political leadership - the
Chairman/Secretary distinction the whole role model is built around),
so they need their own small, genuinely relevant widget rather than
either nothing or the full jurisdiction rollup a Chairman gets.
"""

import datetime

from apps.messaging.services import units_in_subtree

SECRETARY_ROLE_CODES = {
    "national_general_secretary",
    "regional_secretary",
    "constituency_secretary",
    "branch_secretary",
}

WING_ROLE_UNIT_TYPES = {
    "national_youth_organizer": "YOUTH_WING",
    "national_women_organizer": "WOMENS_WING",
    "regional_youth_organizer": "YOUTH_WING",
    "constituency_youth_organizer": "YOUTH_WING",
    "branch_youth_organizer": "YOUTH_WING",
    "regional_women_organizer": "WOMENS_WING",
    "constituency_women_organizer": "WOMENS_WING",
    "branch_women_organizer": "WOMENS_WING",
}


def _secretary_insight(user) -> dict:
    from apps.messaging.documents import Meeting, Report

    unit = user.organizational_unit
    unit_ids = [u.id for u in units_in_subtree(unit)] if unit else []
    now = datetime.datetime.utcnow()

    upcoming_meetings = Meeting.objects(
        target_unit__in=unit_ids, scheduled_start__gte=now, status="SCHEDULED"
    ).order_by("scheduled_start")
    reports_filed = Report.objects(submitted_by=user)

    return {
        "widget": "secretary",
        "title": "Administrative Overview",
        "stats": [
            {"label": "Upcoming Meetings", "value": upcoming_meetings.count()},
            {"label": "Reports You've Filed", "value": reports_filed.count()},
        ],
        "upcoming_meetings": [
            {
                "id": str(m.id),
                "title": m.title,
                "scheduled_start": m.scheduled_start.isoformat(),
            }
            for m in upcoming_meetings[:5]
        ],
    }


def _wing_insight(user, unit_type: str) -> dict:
    """Youth Wing and Women's Wing coordinators. Honest about a real
    structural limitation rather than faking a number: this platform
    does not yet tag individual members as belonging to the Youth or
    Women's Wing separately from the geographic Branch/Constituency/
    Region/National chain they already belong to (see docs on the
    parallel-hierarchy model), so wing membership counts here reflect
    only members whose organizational_unit is literally the wing unit
    itself or a sub-unit of it, not "youth members across the party" -
    that would require a real data-model change, tracked separately,
    not a number invented for this dashboard."""
    from apps.events.documents import Event
    from apps.volunteers.documents import VolunteerOpportunity

    unit = user.organizational_unit
    unit_ids = [u.id for u in units_in_subtree(unit)] if unit else []
    now = datetime.datetime.utcnow()

    upcoming_events = Event.objects(target_unit__in=unit_ids, scheduled_start__gte=now)
    open_opportunities = VolunteerOpportunity.objects(
        target_unit__in=unit_ids, status="OPEN"
    )

    return {
        "widget": "wing",
        "title": f"{user.role.name} Overview",
        "stats": [
            {"label": "Upcoming Events", "value": upcoming_events.count()},
            {
                "label": "Open Volunteer Opportunities",
                "value": open_opportunities.count(),
            },
        ],
        "note": (
            "Wing membership tracking is not yet linked to the geographic "
            "hierarchy - these figures reflect activity in this wing's own "
            "unit tree, not every young/women member across the party."
        ),
    }


def _auditor_insight(user) -> dict:
    """Internal Auditor has no hierarchy.manage, so unlike a Treasurer
    they get no jurisdiction rollup at all, and finance_summary alone
    (transaction totals) doesn't reflect their actual job, which is
    compliance and oversight of what's happening across the system, not
    managing a budget. AuditLog is genuinely global/unscoped (see
    apps.core.audit.AuditLog and apps.core.views.AuditLogListView), so
    unlike every other widget here this one is deliberately not
    filtered to a unit subtree."""
    from apps.core.audit import AuditLog

    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    recent = AuditLog.objects.order_by("-created_at")

    return {
        "widget": "auditor",
        "title": "Audit Overview",
        "stats": [
            {
                "label": "Actions (Last 7 Days)",
                "value": recent.filter(created_at__gte=week_ago).count(),
            },
            {"label": "Total Logged Actions", "value": recent.count()},
        ],
        "recent_actions": [
            {
                "action": log.action,
                "actor_email": log.actor_email,
                "created_at": log.created_at.isoformat(),
            }
            for log in recent[:5]
        ],
    }


def _director_elections_insight(user) -> dict:
    """Director of Elections has elections.manage but is not a
    department head and has no hierarchy.manage, so without this they
    would get nothing at all despite elections being their entire
    constitutional function. Reuses the same real elections data the
    Elections department's own insight already computes."""
    from apps.dashboard.department_insights import _elections_insight

    unit = user.organizational_unit
    result = _elections_insight(None, unit)
    result["title"] = "Elections Overview"
    return result


def _international_relations_insight(user) -> dict:
    """Director of International Relations - real data available:
    External Branch units genuinely exist in this platform's
    auxiliary structure (diaspora chapters), so this reflects actual
    branch count rather than nothing."""
    from apps.hierarchy.documents import OrganizationalUnit

    external_branches = OrganizationalUnit.objects(
        unit_type="EXTERNAL_BRANCH", is_active=True
    )
    return {
        "widget": "international_relations",
        "title": "International Relations Overview",
        "stats": [
            {"label": "External Branches", "value": external_branches.count()},
        ],
        "note": (
            "Diplomatic engagement and delegation tracking are not yet built "
            "as real features in this platform - this reflects only the "
            "External Branch (diaspora chapter) count that already exists."
        ),
    }


AUXILIARY_COORDINATOR_ROLE_CODES = {
    "tein_campus_coordinator",
    "zongo_caucus_coordinator",
    "professionals_forum_convener",
    "external_branch_chairman",
    "council_of_elders_chair",
    "parliamentary_group_leader",
    "functional_committee_chair",
}


def _auxiliary_coordinator_insight(user) -> dict:
    """The 7 auxiliary structure leaders below TEIN National (which
    already has hierarchy.manage and gets the real jurisdiction rollup)
    are deliberately narrow - report.upward only, no hierarchy.manage,
    no department. None of these auxiliary bodies (Zongo Caucus,
    Professionals Forum, External Branches, Council of Elders,
    Parliamentary Group, Functional Committees) have a dedicated
    activity data model in this platform yet (no mediation-case model
    for the Council of Elders, no legislative-activity model for the
    Parliamentary Group, etc.) - rather than invent fake numbers for
    features that don't exist, this shows the two things that are
    genuinely real for every one of them: their unit's actual member
    count, and how many upward reports they've actually filed."""
    from apps.messaging.documents import Report

    unit = user.organizational_unit
    member_count = 0
    if unit:
        from apps.accounts.documents import User as UserDoc

        member_count = UserDoc.objects(organizational_unit=unit, is_active=True).count()
    reports_filed = Report.objects(submitted_by=user).count()

    return {
        "widget": "auxiliary_coordinator",
        "title": f"{user.role.name} Overview",
        "stats": [
            {"label": "Members in Your Unit", "value": member_count},
            {"label": "Reports You've Filed", "value": reports_filed},
        ],
        "note": (
            "Dedicated activity tracking for this structure (mediation cases, "
            "legislative activity, delegation records, etc.) is not yet built "
            "as a real feature here."
        ),
    }


def compute_role_insight(user) -> dict | None:
    """Returns a role-specific widget for the handful of roles that
    need one, or None for everyone else (ordinary members get nothing
    extra here; broad executives already get the jurisdiction rollup
    instead, which is the richer, correct view for them)."""
    if not user.role:
        return None
    code = user.role.code
    if code in SECRETARY_ROLE_CODES:
        return _secretary_insight(user)
    if code in WING_ROLE_UNIT_TYPES:
        return _wing_insight(user, WING_ROLE_UNIT_TYPES[code])
    if code == "internal_auditor":
        return _auditor_insight(user)
    if code == "director_elections":
        return _director_elections_insight(user)
    if code == "director_international_relations":
        return _international_relations_insight(user)
    if code in AUXILIARY_COORDINATOR_ROLE_CODES:
        return _auxiliary_coordinator_insight(user)
    return None
