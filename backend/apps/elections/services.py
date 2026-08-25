from apps.elections.documents import Candidate, EligibleVoter, ResultSubmission, Vote


def branches_in_scope(unit):
    """Every Branch (polling station) in `unit`'s subtree, including
    `unit` itself if it is already a Branch."""
    branches = []
    if unit.unit_type == "BRANCH":
        branches.append(unit)
    branches.extend([u for u in unit.get_descendants() if u.unit_type == "BRANCH"])
    return branches


def units_in_subtree(unit):
    return [unit] + unit.get_descendants()


def _candidate_entry(candidate_totals, candidate):
    candidate_id = str(candidate.id)
    return candidate_totals.setdefault(
        candidate_id,
        {
            "candidate_id": candidate_id,
            "candidate_name": candidate.name,
            "party": candidate.party,
            "votes": 0,
        },
    )


def _finalize_results(candidate_totals):
    results = sorted(candidate_totals.values(), key=lambda c: c["votes"], reverse=True)
    total_votes_cast = sum(c["votes"] for c in results)
    for entry in results:
        entry["percentage"] = (
            round((entry["votes"] / total_votes_cast) * 100, 2)
            if total_votes_cast
            else 0.0
        )

    party_totals = {}
    for entry in results:
        if not entry["party"]:
            continue
        party_entry = party_totals.setdefault(
            entry["party"], {"party": entry["party"], "votes": 0}
        )
        party_entry["votes"] += entry["votes"]
    party_results = sorted(
        party_totals.values(), key=lambda p: p["votes"], reverse=True
    )
    for entry in party_results:
        entry["percentage"] = (
            round((entry["votes"] / total_votes_cast) * 100, 2)
            if total_votes_cast
            else 0.0
        )

    return results, total_votes_cast, party_results


def _aggregate_from_collation(election, unit, unit_ids, position):
    """Branch-level (polling-station) collation - real paper-ballot counts
    submitted by an appointed branch executive. Used for general elections
    and any election with no direct electorate selected."""
    submissions = ResultSubmission.objects(election=election, branch_unit__in=unit_ids)
    submissions = (
        submissions.filter(position=position)
        if position is not None
        else submissions.filter(position=None)
    )
    submissions = list(submissions)

    candidate_totals = {}
    total_registered_voters = 0
    total_valid_votes = 0
    total_rejected_votes = 0
    verified_count = 0
    disputed_count = 0

    for submission in submissions:
        total_registered_voters += submission.total_registered_voters or 0
        total_valid_votes += submission.total_valid_votes or 0
        total_rejected_votes += submission.total_rejected_votes or 0
        if submission.status == "VERIFIED":
            verified_count += 1
        elif submission.status == "DISPUTED":
            disputed_count += 1
        for tally in submission.tallies:
            _candidate_entry(candidate_totals, tally.candidate)["votes"] += tally.votes

    results, total_votes_cast, party_results = _finalize_results(candidate_totals)

    expected_branches = branches_in_scope(unit)
    branches_reported = len({s.branch_unit.id for s in submissions})
    branches_expected = len(expected_branches)
    turnout_percentage = (
        round(
            (total_valid_votes + total_rejected_votes) / total_registered_voters * 100,
            2,
        )
        if total_registered_voters
        else None
    )

    return {
        "mode": "BRANCH_COLLATION",
        "results": results,
        "party_results": party_results,
        "leading_candidate": results[0] if results else None,
        "total_votes_cast": total_votes_cast,
        "total_registered_voters": total_registered_voters or None,
        "total_valid_votes": total_valid_votes or None,
        "total_rejected_votes": total_rejected_votes or None,
        "turnout_percentage": turnout_percentage,
        "branches_expected": branches_expected,
        "branches_reported": branches_reported,
        "reporting_percentage": (
            round(branches_reported / branches_expected * 100, 2)
            if branches_expected
            else None
        ),
        "verified_submissions": verified_count,
        "disputed_submissions": disputed_count,
        "is_fully_reported": branches_expected > 0
        and branches_reported == branches_expected,
    }


def _aggregate_from_direct_voting(election, position):
    """Direct digital voting - every eligible voter casts their own
    ballot in-app. Used for internal party elections with a selected
    electorate, and for the two mandatory-open primary types where
    "eligible" means every active member (of the constituency, for a
    parliamentary primary) rather than a curated EligibleVoter list."""
    from apps.elections.constants import MANDATORY_OPEN_ELECTORATE_TYPES

    votes = Vote.objects(election=election)
    votes = (
        votes.filter(position=position)
        if position is not None
        else votes.filter(position=None)
    )
    votes = list(votes)

    candidate_totals = {}
    for vote in votes:
        _candidate_entry(candidate_totals, vote.candidate)["votes"] += 1

    results, total_votes_cast, party_results = _finalize_results(candidate_totals)

    if election.election_type in MANDATORY_OPEN_ELECTORATE_TYPES:
        from apps.accounts.documents import User

        if election.election_type == "PARLIAMENTARY_PRIMARY":
            eligible_unit_ids = [u.id for u in units_in_subtree(election.scope_unit)]
            eligible_count = User.objects(
                organizational_unit__in=eligible_unit_ids, is_active=True
            ).count()
        else:
            eligible_count = User.objects(is_active=True).count()
    else:
        eligible_count = EligibleVoter.objects(election=election).count()

    votes_cast_count = len(votes)

    return {
        "mode": "DIRECT_VOTING",
        "results": results,
        "party_results": party_results,
        "leading_candidate": results[0] if results else None,
        "total_votes_cast": total_votes_cast,
        "eligible_voters_count": eligible_count,
        "votes_cast_count": votes_cast_count,
        "turnout_percentage": (
            round(votes_cast_count / eligible_count * 100, 2)
            if eligible_count
            else None
        ),
        "is_fully_reported": eligible_count > 0 and votes_cast_count == eligible_count,
    }


def aggregate_results(election, unit, position=None):
    """
    Automatic roll-up analysis for `election` across every Branch in
    `unit`'s subtree (or `unit` itself, if it's already a Branch) - this
    is what lets National see live, computed results the moment branches
    start submitting, without anyone manually adding up polling-station
    sheets.

    Auto-detects the mechanism: if the election has a selected electorate
    (EligibleVoter records exist), results come from direct digital votes;
    otherwise from branch-level collation sheets. Every candidate's `party`
    is carried through and rolled up into `party_results` too, so
    "who's winning, NDC or NPP or others" is answered directly.
    """
    unit_ids = [u.id for u in units_in_subtree(unit)]

    from apps.elections.constants import MANDATORY_OPEN_ELECTORATE_TYPES

    if (
        election.election_type in MANDATORY_OPEN_ELECTORATE_TYPES
        or EligibleVoter.objects(election=election).first() is not None
    ):
        body = _aggregate_from_direct_voting(election, position)
    else:
        body = _aggregate_from_collation(election, unit, unit_ids, position)

    return {
        "election_id": str(election.id),
        "organizational_unit": {
            "id": str(unit.id),
            "name": unit.name,
            "unit_type": unit.unit_type,
        },
        "position": position,
        **body,
    }


def distinct_positions(election):
    """The set of contested positions for a multi-race election (empty
    list for a single-race election/poll)."""
    return [p for p in Candidate.objects(election=election).distinct("position") if p]
