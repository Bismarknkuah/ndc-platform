from apps.finance.documents import FinanceRecord


def units_in_subtree(unit):
    return [unit] + unit.get_descendants()


def summarize_finance(unit, start_date=None, end_date=None, status="APPROVED"):
    """
    Rolls up every FinanceRecord anywhere in `unit`'s subtree: total
    income, total expense, net balance, and a breakdown by category.
    Defaults to APPROVED records only (pass status=None for everything,
    including still-pending entries).
    """
    unit_ids = [u.id for u in units_in_subtree(unit)]
    qs = FinanceRecord.objects(organizational_unit__in=unit_ids)
    if status:
        qs = qs.filter(status=status)
    if start_date:
        qs = qs.filter(record_date__gte=start_date)
    if end_date:
        qs = qs.filter(record_date__lte=end_date)

    records = list(qs)
    total_income = sum(
        (r.amount for r in records if r.record_type == "INCOME"), start=0
    )
    total_expense = sum(
        (r.amount for r in records if r.record_type == "EXPENSE"), start=0
    )

    category_totals = {}
    for record in records:
        key = (record.record_type, record.category)
        category_totals.setdefault(
            key,
            {
                "record_type": record.record_type,
                "category": record.category,
                "total": 0,
            },
        )
        category_totals[key]["total"] += record.amount

    for entry in category_totals.values():
        entry["total"] = str(entry["total"])

    return {
        "organizational_unit": {
            "id": str(unit.id),
            "name": unit.name,
            "unit_type": unit.unit_type,
        },
        "total_income": str(total_income),
        "total_expense": str(total_expense),
        "net_balance": str(total_income - total_expense),
        "record_count": len(records),
        "by_category": sorted(
            category_totals.values(), key=lambda c: c["total"], reverse=True
        ),
    }
