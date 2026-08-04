"""
Constants for the Disciplinary Committee system - Articles 46 and 47 of
the NDC Constitution, read in full and modeled deliberately as its own
system rather than folded into the general-purpose Complaints module:
the constitution describes a specific, timed, quasi-judicial process
with its own standing committee, not an arbitrary complaint inbox.
"""

# Article 46(8): grounds for which a member may be subjected to discipline.
DISCIPLINE_GROUND_CHOICES = [
    ("CONSTITUTIONAL_BREACH", "Breach of the Constitution"),
    ("ANTI_PARTY_CONDUCT", "Anti-Party conduct or activity"),
    ("INSUBORDINATION", "Insubordination or negligence"),
    ("CONFIDENTIALITY_BREACH", "Unauthorised disclosure of confidential information"),
    ("OTHER", "Other conduct adversely affecting the Party"),
]

# Article 46(9): the measures a case may conclude with.
DISCIPLINARY_MEASURE_CHOICES = [
    ("EXPULSION", "Expulsion"),
    ("SUSPENSION", "Suspension for a specific period"),
    ("REMOVAL_FROM_OFFICE", "Removal from office"),
    ("INELIGIBILITY", "Ineligibility to hold office"),
    ("FINE", "Fine"),
    ("REPRIMAND", "Reprimand"),
]

CASE_STATUS_CHOICES = [
    ("REPORTED", "Reported"),
    ("CONVENED", "Committee convened"),
    ("RECOMMENDED", "Recommendation made"),
    ("DECIDED", "Decided by Executive Committee"),
    ("APPEALED", "Under appeal"),
    ("CLOSED", "Closed"),
]

SUSPENSION_STATUS_CHOICES = [
    ("ACTIVE", "Active"),
    ("REFERRED", "Referred to Disciplinary Committee"),
    ("LAPSED", "Lapsed (not referred in time)"),
    ("ENDED", "Ended"),
]

# Article 46(1)/(4): a precautionary suspension (before proceedings begin)
# runs at most 6 months, renewable once for up to 5 further months.
INITIAL_SUSPENSION_MAX_DAYS = 183  # ~6 months
SUSPENSION_RENEWAL_MAX_DAYS = 152  # ~5 months
# Article 46(2)/(3): must be referred to the Disciplinary Committee within
# one month of the suspension, or it lapses.
SUSPENSION_REFERRAL_DEADLINE_DAYS = 30
# Article 47(3)/(4): committee must convene within 14 days of the
# complaint, and conclude within 30 days of its first sitting.
CASE_CONVENE_DEADLINE_DAYS = 14
CASE_CONCLUDE_DEADLINE_DAYS = 30
# Article 46(11)(a) / 47(6): appeal window after a decision is notified.
APPEAL_WINDOW_DAYS = 14
