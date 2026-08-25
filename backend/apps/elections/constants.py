"""
One unified model covers everything the Election & IT Director organizes:
a national general election, an internal party election (possibly with
multiple contested positions - Chairman, Secretary, ... - decided in the
same event), or a lightweight poll/data-gathering exercise. All three
share the same collation mechanics: candidates/options, one result
submission per polling station (Branch), and automatic roll-up analysis
at every level of the hierarchy up to National.
"""

ELECTION_TYPE_CHOICES = [
    ("NATIONAL_GENERAL", "National General Election"),
    ("PARTY_INTERNAL", "Internal Party Election"),
    (
        "PRESIDENTIAL_PRIMARY",
        "Presidential Primary (open to all active members, by Supreme Court ruling)",
    ),
    (
        "PARLIAMENTARY_PRIMARY",
        "Parliamentary Primary (open to all active members of the constituency, by Supreme Court ruling)",
    ),
    ("POLL", "Poll / Data Gathering"),
    ("OTHER", "Other"),
]

# Election types the Supreme Court has ruled must be open to every active
# member (of the relevant constituency, for a parliamentary primary) - the
# Election/IT Director cannot curate the electorate for these; eligibility
# is a dynamic, continuously-evaluated status (active membership), not a
# one-time snapshot of selected voters. See is_eligible_voter and
# aggregate_results in this app, both of which special-case these types.
MANDATORY_OPEN_ELECTORATE_TYPES = ("PRESIDENTIAL_PRIMARY", "PARLIAMENTARY_PRIMARY")

ELECTION_STATUS_CHOICES = [
    ("DRAFT", "Draft"),
    ("OPEN", "Open for Voting"),
    ("COLLATION", "Collation in Progress"),
    ("COMPLETED", "Completed"),
    ("CANCELLED", "Cancelled"),
]

RESULT_STATUS_CHOICES = [
    ("SUBMITTED", "Submitted"),
    ("VERIFIED", "Verified"),
    ("DISPUTED", "Disputed"),
]

ELECTION_REQUEST_STATUS_CHOICES = [
    ("PENDING", "Pending Review"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
    ("FULFILLED", "Fulfilled"),
]

POLLING_AGENT_ROLE_CHOICES = [
    ("PARTY_AGENT", "Party Agent"),
    ("PRESIDING_OFFICER_LIAISON", "Presiding Officer Liaison"),
    ("OBSERVER", "Observer"),
]
