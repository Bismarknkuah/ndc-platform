import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    IntField,
    ReferenceField,
    StringField,
)

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.elections.constants import (
    ELECTION_REQUEST_STATUS_CHOICES,
    ELECTION_STATUS_CHOICES,
    ELECTION_TYPE_CHOICES,
    POLLING_AGENT_ROLE_CHOICES,
    RESULT_STATUS_CHOICES,
)
from apps.hierarchy.documents import OrganizationalUnit


class Election(TimestampedDocument):
    """
    A general election, an internal party election, or a poll. `scope_unit`
    is the top of the tree this election runs across - results collate
    upward from every Branch (polling station) in its subtree to here.
    """

    title = StringField(required=True, max_length=200)
    description = StringField(default="")
    election_type = StringField(required=True, choices=ELECTION_TYPE_CHOICES)
    scope_unit = ReferenceField(OrganizationalUnit, required=True)
    status = StringField(choices=ELECTION_STATUS_CHOICES, default="DRAFT")

    organized_by = ReferenceField(User, required=True)
    start_date = DateTimeField(required=True)
    end_date = DateTimeField(required=True)

    meta = {
        "collection": "elections",
        "indexes": ["scope_unit", "status", "election_type", "-created_at"],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"[{self.election_type}] {self.title}"


class ElectionRequest(TimestampedDocument):
    """
    A formal request from a department or unit executive asking the
    Election/IT Director to organize an election for them - since
    election-organizing authority is centralized exclusively to that
    role (see apps.elections.permissions.can_manage_election), every
    other department or unit that needs an election run must go
    through this request/approval flow rather than organizing one
    themselves.
    """

    requested_by = ReferenceField(User, required=True)
    target_unit = ReferenceField(OrganizationalUnit, required=True)
    election_type = StringField(required=True, choices=ELECTION_TYPE_CHOICES)
    title = StringField(required=True, max_length=200)
    reason = StringField(required=True)
    requested_start_date = DateTimeField(null=True)
    requested_end_date = DateTimeField(null=True)

    status = StringField(choices=ELECTION_REQUEST_STATUS_CHOICES, default="PENDING")
    reviewed_by = ReferenceField(User, null=True)
    review_notes = StringField(default="")
    reviewed_at = DateTimeField(null=True)

    # Set once an Election/IT Director acts on this request by actually
    # creating the election - links the request to the real outcome so
    # the requester can see it went from "asked" to "organized",
    # without this model needing to duplicate any of the Election
    # model's own fields.
    fulfilled_election = ReferenceField(Election, null=True)

    meta = {
        "collection": "election_requests",
        "indexes": ["target_unit", "status", "requested_by", "-created_at"],
        "ordering": ["-created_at"],
    }

    def approve(self, reviewer, notes=""):
        self.status = "APPROVED"
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.reviewed_at = datetime.datetime.utcnow()
        self.save()

    def reject(self, reviewer, notes=""):
        self.status = "REJECTED"
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.reviewed_at = datetime.datetime.utcnow()
        self.save()

    def fulfill(self, election):
        self.status = "FULFILLED"
        self.fulfilled_election = election
        self.save()

    def __str__(self):
        return f"[{self.status}] {self.title} for {self.target_unit.name}"


class Candidate(TimestampedDocument):
    """
    A contestant (or poll option) in an Election. `position` groups
    candidates into separate races within one Election - e.g. a single
    internal party election event might contest "National Chairman" and
    "National Treasurer" simultaneously, or a general election contests
    "President" and "MP - <Constituency>" independently; each position has
    its own candidate list and is tallied separately. Leave `position`
    blank for a single-race election or a simple poll. `party` is for
    multi-party general elections ("NDC", "NPP", "Independent", ...) so
    results can be broken down by party as well as by candidate; leave
    blank for internal party elections where every candidate is NDC.
    """

    election = ReferenceField(Election, required=True)
    name = StringField(required=True, max_length=200)
    description = StringField(default="")
    position = StringField(null=True, max_length=150)
    party = StringField(null=True, max_length=100)
    display_order = IntField(default=0)
    # Raw base64 image data (no "data:" prefix), same pattern as the
    # membership-card QR codes - no external file storage dependency.
    # Capped at ~2MB of encoded data by the serializer, not here.
    photo_base64 = StringField(null=True)

    meta = {
        "collection": "candidates",
        "indexes": ["election", "position", "party"],
        "ordering": ["display_order", "name"],
    }

    def __str__(self):
        return f"{self.name} ({self.position or self.election.title})"


class CandidateTally(EmbeddedDocument):
    candidate = ReferenceField(Candidate, required=True)
    votes = IntField(required=True, min_value=0)


class ResultSubmission(TimestampedDocument):
    """
    One polling station's (Branch's) official result sheet for one race
    (election + position) - the collation unit. Exactly one submission is
    accepted per (election, branch_unit, position); a branch executive
    submitting after the fact amends it (PATCH) rather than creating a
    second, conflicting one.
    """

    election = ReferenceField(Election, required=True)
    branch_unit = ReferenceField(OrganizationalUnit, required=True)
    position = StringField(null=True, max_length=150)

    submitted_by = ReferenceField(User, required=True)
    tallies = EmbeddedDocumentListField(CandidateTally)

    # Photographic evidence of the physical result sheet ("pink sheet"),
    # same base64-in-Mongo pattern as candidate photos and membership QR
    # codes - no external file storage dependency. Required by the
    # serializer for new submissions; nullable here so existing records
    # from before this field existed remain valid.
    collation_sheet_photo_base64 = StringField(null=True)

    total_registered_voters = IntField(null=True, min_value=0)
    total_valid_votes = IntField(null=True, min_value=0)
    total_rejected_votes = IntField(null=True, min_value=0)

    status = StringField(choices=RESULT_STATUS_CHOICES, default="SUBMITTED")
    verified_by = ReferenceField(User, null=True)
    verified_at = DateTimeField(null=True)

    meta = {
        "collection": "election_result_submissions",
        "indexes": [
            {"fields": ["election", "branch_unit", "position"], "unique": True},
            "status",
        ],
        "ordering": ["-created_at"],
    }

    def mark_verified(self, by_user):
        self.status = "VERIFIED"
        self.verified_by = by_user
        self.verified_at = datetime.datetime.utcnow()

    def mark_disputed(self, by_user):
        self.status = "DISPUTED"
        self.verified_by = by_user
        self.verified_at = datetime.datetime.utcnow()

    def __str__(self):
        return f"{self.election.title} @ {self.branch_unit.name} ({self.position or 'single race'})"


class EligibleVoter(TimestampedDocument):
    """
    Marks `user` as allowed to cast a ballot directly in `election` (the
    Election & IT Director's electorate selection for an internal party
    election). Adding someone notifies them - "those who qualify have to
    see notification and use their portal to vote". The presence of any
    EligibleVoter records for an election is what switches its results
    from branch-level collation to direct digital voting (see
    apps.elections.services.aggregate_results).
    """

    election = ReferenceField(Election, required=True)
    user = ReferenceField(User, required=True)
    added_by = ReferenceField(User, required=True)

    meta = {
        "collection": "election_eligible_voters",
        "indexes": [{"fields": ["election", "user"], "unique": True}],
    }

    def __str__(self):
        return f"{self.user.full_name} eligible for {self.election.title}"


class Vote(TimestampedDocument):
    """
    One eligible voter's ballot for one race (election + position) - cast
    directly through their portal, not submitted on their behalf. Exactly
    one vote per (election, position, voter), enforced at the database
    level so double-voting is structurally impossible, not just
    discouraged by application logic.
    """

    election = ReferenceField(Election, required=True)
    position = StringField(null=True, max_length=150)
    voter = ReferenceField(User, required=True)
    candidate = ReferenceField(Candidate, required=True)
    cast_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "election_votes",
        "indexes": [{"fields": ["election", "position", "voter"], "unique": True}],
    }

    def __str__(self):
        return f"{self.voter.full_name} voted in {self.election.title} ({self.position or 'single race'})"


class PollingAgentAssignment(TimestampedDocument):
    """
    Election-day logistics: who is physically assigned to a Branch
    (polling station) for a given election, distinct from *who may submit
    the result sheet* (that's the Elections/IT department designation on
    the branch itself, reused across elections). An agent checks in on
    the day and confirms materials received - simple, real accountability
    without inventing a separate materials-tracking subsystem.
    """

    election = ReferenceField(Election, required=True)
    branch_unit = ReferenceField(OrganizationalUnit, required=True)
    agent = ReferenceField(User, required=True)
    role = StringField(required=True, choices=POLLING_AGENT_ROLE_CHOICES)
    assigned_by = ReferenceField(User, required=True)

    checked_in_at = DateTimeField(null=True)
    materials_confirmed = BooleanField(default=False)
    notes = StringField(default="")

    meta = {
        "collection": "polling_agent_assignments",
        "indexes": [
            "election",
            "branch_unit",
            {"fields": ["election", "branch_unit", "agent"], "unique": True},
        ],
    }

    def check_in(self):
        self.checked_in_at = datetime.datetime.utcnow()

    def __str__(self):
        return f"{self.agent.full_name} ({self.role}) @ {self.branch_unit.name} for {self.election.title}"
