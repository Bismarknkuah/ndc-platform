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
    ("POLL", "Poll / Data Gathering"),
    ("OTHER", "Other"),
]

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

POLLING_AGENT_ROLE_CHOICES = [
    ("PARTY_AGENT", "Party Agent"),
    ("PRESIDING_OFFICER_LIAISON", "Presiding Officer Liaison"),
    ("OBSERVER", "Observer"),
]
