def can_register_kiosk(user, election) -> bool:
    """Registering a physical kiosk for an election is part of organizing
    it - the same authority as everything else in can_manage_election
    (the Election/IT Director role, or department-based Elections/IT
    authority over the election's own scope_unit)."""
    from apps.elections.permissions import can_manage_election

    return can_manage_election(user, election.scope_unit)
