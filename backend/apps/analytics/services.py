import calendar
import datetime

from apps.accounts.documents import User
from apps.departments.documents import DepartmentAssignment, TaskAssignment
from apps.messaging.services import units_in_subtree


def compute_membership_analytics(unit) -> dict:
    unit_ids = [u.id for u in units_in_subtree(unit)]
    members = list(User.objects(organizational_unit__in=unit_ids, is_active=True))

    gender_breakdown = {"MALE": 0, "FEMALE": 0, "OTHER": 0, "UNSPECIFIED": 0}
    executive_count = 0
    for member in members:
        key = member.gender or "UNSPECIFIED"
        gender_breakdown[key] = gender_breakdown.get(key, 0) + 1
        if member.role and member.role.is_executive:
            executive_count += 1

    now = datetime.datetime.utcnow()
    growth_by_month = []
    for i in range(11, -1, -1):
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_start = datetime.datetime(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        month_end = datetime.datetime(year, month, days_in_month, 23, 59, 59)
        count = sum(
            1
            for m in members
            if m.date_joined and month_start <= m.date_joined <= month_end
        )
        growth_by_month.append(
            {"month": month_start.strftime("%Y-%m"), "new_members": count}
        )

    return {
        "organizational_unit": {
            "id": str(unit.id),
            "name": unit.name,
            "unit_type": unit.unit_type,
        },
        "total_members": len(members),
        "executive_count": executive_count,
        "ordinary_member_count": len(members) - executive_count,
        "gender_breakdown": gender_breakdown,
        "growth_last_12_months": growth_by_month,
    }


def compute_department_analytics(department, unit) -> dict:
    unit_ids = [u.id for u in units_in_subtree(unit)]
    team_user_ids = [
        a.user.id
        for a in DepartmentAssignment.objects(
            department=department, organizational_unit__in=unit_ids, is_active=True
        )
    ]
    tasks = list(
        TaskAssignment.objects(department=department, assigned_to__in=team_user_ids)
    )

    status_counts = {"PENDING": 0, "ACKNOWLEDGED": 0, "COMPLETED": 0, "CANCELLED": 0}
    for task in tasks:
        status_counts[task.status] = status_counts.get(task.status, 0) + 1

    completable = (
        status_counts["COMPLETED"]
        + status_counts["PENDING"]
        + status_counts["ACKNOWLEDGED"]
    )
    completion_rate = (
        round(status_counts["COMPLETED"] / completable * 100, 2)
        if completable
        else None
    )

    return {
        "department": {"id": str(department.id), "name": department.name},
        "organizational_unit": {
            "id": str(unit.id),
            "name": unit.name,
            "unit_type": unit.unit_type,
        },
        "team_size": len(team_user_ids),
        "total_tasks": len(tasks),
        "status_breakdown": status_counts,
        "completion_rate_percentage": completion_rate,
    }


def compute_ground_intelligence(unit, item_limit: int = 15) -> dict:
    """
    Real, on-the-ground situation for a unit and everything beneath it -
    the actual titles and descriptions members and executives have
    already submitted through Complaints, Welfare, and upward Reports,
    not a summary invented from nothing. This is deliberately the raw
    material an AI briefing gets built from (see
    apps.executive_ai.services.ground_situation_briefing) - the model
    only ever sees what real people actually reported.

    `item_limit` caps how many of the most recent items from each
    source get included, so a large region's payload stays bounded
    rather than growing without limit as more gets reported over time.
    """
    from apps.complaints.documents import Complaint
    from apps.discipline.documents import DisciplinaryCase
    from apps.messaging.documents import Report
    from apps.welfare.documents import WelfareRequest

    unit_ids = [u.id for u in units_in_subtree(unit)]

    complaints_qs = Complaint.objects(target_unit__in=unit_ids).order_by("-created_at")
    welfare_qs = WelfareRequest.objects(organizational_unit__in=unit_ids).order_by(
        "-created_at"
    )
    reports_qs = Report.objects(target_unit__in=unit_ids).order_by("-created_at")

    pending_complaints = complaints_qs.filter(status__in=["SUBMITTED", "UNDER_REVIEW"])
    pending_welfare = welfare_qs.filter(status__in=["SUBMITTED", "UNDER_REVIEW"])
    pending_discipline = DisciplinaryCase.objects(
        organizational_unit__in=unit_ids,
        is_active=True,
        status__nin=["DECIDED", "CLOSED"],
    )

    return {
        "organizational_unit": {
            "id": str(unit.id),
            "name": unit.name,
            "unit_type": unit.unit_type,
        },
        "counts": {
            "pending_complaints": pending_complaints.count(),
            "pending_welfare_requests": pending_welfare.count(),
            "pending_discipline_cases": pending_discipline.count(),
            "total_reports": reports_qs.count(),
        },
        "recent_complaints": [
            {
                "subject": c.subject,
                "description": c.description,
                "type": c.complaint_type,
                "status": c.status,
                "unit": c.submitting_unit.name if c.submitting_unit else None,
                "created_at": c.created_at.isoformat(),
                "is_anonymous": c.is_anonymous,
                # The real name, always - compute_ground_intelligence is
                # only ever reached through a view already gated to the
                # same top-leadership authority that holds reveal rights
                # (see apps.complaints.permissions.can_reveal_reporter_identity).
                # Whether a downstream report or speech generated from
                # this actually includes it is a separate, later choice
                # (see apps.executive_ai.services.generate_official_report),
                # not a re-check of authority that has already been made.
                "reported_by": c.submitted_by.full_name,
                "reported_executive": (
                    c.reported_user.full_name if c.reported_user else None
                ),
            }
            for c in pending_complaints[:item_limit]
        ],
        "recent_welfare_requests": [
            {
                "category": w.category,
                "description": w.description,
                "status": w.status,
                "unit": w.organizational_unit.name if w.organizational_unit else None,
                "created_at": w.created_at.isoformat(),
            }
            for w in pending_welfare[:item_limit]
        ],
        "recent_reports": [
            {
                "title": r.title,
                "body": r.body,
                "status": r.status,
                "unit": r.submitting_unit.name if r.submitting_unit else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in reports_qs[:item_limit]
        ],
    }
