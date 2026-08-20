"""
Real, department-specific dashboard content - built systematically
rather than as 14 bespoke one-off pages. Each department gets a small
function that pulls the data actually relevant to that department's
real work, reusing services and models that already exist elsewhere in
the platform (Finance, Elections, Messaging, Membership, Complaints,
Welfare, Discipline, Events) rather than inventing new per-department
data models. A department with no bespoke builder yet falls back to a
generic team/task summary rather than showing nothing.
"""

import datetime

from apps.messaging.services import units_in_subtree


def _finance_insight(department, unit) -> dict:
    from apps.finance.services import summarize_finance

    summary = summarize_finance(unit)
    return {
        "widget": "finance",
        "stats": [
            {"label": "Net Balance", "value": f"GHS {summary['net_balance']}"},
            {"label": "Total Income", "value": f"GHS {summary['total_income']}"},
            {"label": "Total Expense", "value": f"GHS {summary['total_expense']}"},
        ],
    }


def _elections_insight(department, unit) -> dict:
    from apps.elections.documents import Election

    unit_ids = [u.id for u in units_in_subtree(unit)]
    qs = Election.objects(scope_unit__in=unit_ids)
    return {
        "widget": "elections",
        "stats": [
            {"label": "Active Elections", "value": qs.filter(status="OPEN").count()},
            {"label": "In Collation", "value": qs.filter(status="COLLATION").count()},
            {"label": "Total Run", "value": qs.count()},
        ],
    }


def _communications_insight(department, unit) -> dict:
    from apps.messaging.documents import Broadcast

    unit_ids = [u.id for u in units_in_subtree(unit)]
    thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    qs = Broadcast.objects(target_unit__in=unit_ids)
    return {
        "widget": "communications",
        "stats": [
            {
                "label": "Broadcasts (30 days)",
                "value": qs.filter(created_at__gte=thirty_days_ago).count(),
            },
            {"label": "Total Broadcasts", "value": qs.count()},
        ],
    }


def _membership_insight(department, unit) -> dict:
    from apps.analytics.services import compute_membership_analytics

    analytics = compute_membership_analytics(unit)
    growth = analytics["growth_last_12_months"]
    latest_month = growth[-1] if growth else None
    return {
        "widget": "membership",
        "stats": [
            {"label": "Total Members", "value": analytics["total_members"]},
            {
                "label": "This Month",
                "value": latest_month["new_members"] if latest_month else 0,
            },
            {"label": "Executives", "value": analytics["executive_count"]},
        ],
    }


def _legal_affairs_insight(department, unit) -> dict:
    from apps.complaints.documents import Complaint
    from apps.discipline.documents import DisciplinaryCase

    unit_ids = [u.id for u in units_in_subtree(unit)]
    return {
        "widget": "legal",
        "stats": [
            {
                "label": "Pending Complaints",
                "value": Complaint.objects(
                    target_unit__in=unit_ids, status__in=["SUBMITTED", "UNDER_REVIEW"]
                ).count(),
            },
            {
                "label": "Open Discipline Cases",
                "value": DisciplinaryCase.objects(
                    organizational_unit__in=unit_ids,
                    is_active=True,
                    status__nin=["DECIDED", "CLOSED"],
                ).count(),
            },
        ],
    }


def _welfare_insight(department, unit) -> dict:
    from apps.welfare.documents import WelfareRequest

    unit_ids = [u.id for u in units_in_subtree(unit)]
    qs = WelfareRequest.objects(organizational_unit__in=unit_ids)
    return {
        "widget": "welfare",
        "stats": [
            {
                "label": "Pending Requests",
                "value": qs.filter(status__in=["SUBMITTED", "UNDER_REVIEW"]).count(),
            },
            {"label": "Disbursed", "value": qs.filter(status="DISBURSED").count()},
        ],
    }


def _events_insight(department, unit) -> dict:
    from apps.events.documents import Event

    unit_ids = [u.id for u in units_in_subtree(unit)]
    now = datetime.datetime.utcnow()
    qs = Event.objects(target_unit__in=unit_ids)
    return {
        "widget": "events",
        "stats": [
            {"label": "Upcoming", "value": qs.filter(scheduled_start__gte=now).count()},
            {"label": "Total Events", "value": qs.count()},
        ],
    }


def _generic_insight(department, unit) -> dict:
    from apps.departments.documents import DepartmentAssignment, TaskAssignment

    unit_ids = [u.id for u in units_in_subtree(unit)]
    team_user_ids = [
        a.user.id
        for a in DepartmentAssignment.objects(
            department=department, organizational_unit__in=unit_ids, is_active=True
        )
    ]
    tasks = TaskAssignment.objects(department=department, assigned_to__in=team_user_ids)
    return {
        "widget": "generic",
        "stats": [
            {"label": "Team Size", "value": len(team_user_ids)},
            {"label": "Pending Tasks", "value": tasks.filter(status="PENDING").count()},
        ],
    }


# Maps a department's code to the function that computes its real
# insights. Deliberately not every one of the 14 departments has a
# bespoke entry - Organizing, Research & Innovation, the four Article 32
# committees, and Information Technology currently fall through to
# _generic_insight rather than being forced into a stat shape that would
# not actually reflect their work. Add an entry here once that
# department has a real underlying data model worth surfacing.
DEPARTMENT_INSIGHT_BUILDERS = {
    "finance": _finance_insight,
    "elections": _elections_insight,
    "communications": _communications_insight,
    "membership": _membership_insight,
    "legal-affairs": _legal_affairs_insight,
    "womens-affairs": _welfare_insight,
    "youth-affairs": _events_insight,
    # The Election IT Director role (election_it_director) is a
    # combined Elections + IT function - the elections builder is
    # genuinely more relevant to their real work than the generic
    # team-size fallback every other unmapped department gets.
    "it": _elections_insight,
}


def compute_department_insight(department, unit) -> dict:
    builder = DEPARTMENT_INSIGHT_BUILDERS.get(department.code, _generic_insight)
    return builder(department, unit)
