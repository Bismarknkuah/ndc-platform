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
