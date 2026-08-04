import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
)

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.hierarchy.documents import OrganizationalUnit
from apps.discipline.constants import (
    CASE_STATUS_CHOICES,
    DISCIPLINARY_MEASURE_CHOICES,
    DISCIPLINE_GROUND_CHOICES,
    SUSPENSION_STATUS_CHOICES,
)


class DisciplinaryCommittee(TimestampedDocument):
    """
    The standing 3-member Disciplinary Committee at one organizational
    unit (Article 46(5)): "every level of the Party organisation except
    the district shall have a 3-member Disciplinary Committee elected by
    the Executives at that level who shall not be members of the
    Executive". One active committee per unit - re-electing replaces the
    roster rather than creating a second standing committee.
    """

    organizational_unit = ReferenceField(OrganizationalUnit, required=True, unique=True)
    members = ListField(ReferenceField(User), required=True)
    elected_at = DateTimeField(default=datetime.datetime.utcnow)
    is_active = BooleanField(default=True)

    meta = {
        "collection": "disciplinary_committees",
        "indexes": ["organizational_unit"],
    }


class DisciplinaryCase(TimestampedDocument):
    """
    A disciplinary matter under Articles 46-47. Deliberately modeled with
    its own timelines and a self-referencing `parent_case` for appeals -
    "a member who is aggrieved by the decision of a Disciplinary
    Committee may appeal in writing... to the Executive Committee of the
    immediate higher level" (Article 47(6)) - rather than reusing the
    general Complaints app, since this is a specific, timed,
    quasi-judicial process with statutory deadlines, not an arbitrary
    complaint inbox.
    """

    organizational_unit = ReferenceField(OrganizationalUnit, required=True)
    committee = ReferenceField(DisciplinaryCommittee, required=False)
    respondent = ReferenceField(User, required=True)
    reported_by = ReferenceField(User, required=True)
    grounds = StringField(choices=DISCIPLINE_GROUND_CHOICES, required=True)
    description = StringField(required=True)
    status = StringField(choices=CASE_STATUS_CHOICES, default="REPORTED")

    reported_at = DateTimeField(default=datetime.datetime.utcnow)
    convened_at = DateTimeField(null=True)
    recommendation = StringField(default="")
    recommended_measure = StringField(choices=DISCIPLINARY_MEASURE_CHOICES, null=True)
    recommended_at = DateTimeField(null=True)

    final_decision = StringField(default="")
    final_measure = StringField(choices=DISCIPLINARY_MEASURE_CHOICES, null=True)
    decided_at = DateTimeField(null=True)
    decided_by = ReferenceField(User, null=True)
    varied_from_recommendation = BooleanField(default=False)

    # An appeal is modeled as a new case at the next-higher unit,
    # pointing back at the case being appealed - not a special sub-object,
    # since Article 47(8) says an appellate Disciplinary Committee is
    # "guided by the provisions of Articles 45 and 46" i.e. the same
    # process, just one level up.
    parent_case = ReferenceField("self", null=True)
    is_active = BooleanField(default=True)

    meta = {
        "collection": "disciplinary_cases",
        "indexes": ["organizational_unit", "respondent", "-created_at"],
    }


class MemberSuspension(TimestampedDocument):
    """
    A precautionary suspension imposed directly by an Executive Committee
    BEFORE disciplinary proceedings begin (Article 46(1)): "the Executive
    Committee at each level may suspend a member... for a period not more
    than six months before the commencement of disciplinary proceedings
    ... if it is considered that the suspension is in the interest of the
    Party." Must be referred to the Disciplinary Committee within one
    month or it lapses (46(2)/(3)); may be renewed once for up to five
    further months (46(4)).
    """

    user = ReferenceField(User, required=True)
    organizational_unit = ReferenceField(OrganizationalUnit, required=True)
    suspended_by = ReferenceField(User, required=True)
    reason = StringField(required=True)
    status = StringField(choices=SUSPENSION_STATUS_CHOICES, default="ACTIVE")

    suspended_at = DateTimeField(default=datetime.datetime.utcnow)
    referred_at = DateTimeField(null=True)
    renewed_at = DateTimeField(null=True)
    renewal_count = IntField(default=0)
    related_case = ReferenceField(DisciplinaryCase, null=True)

    meta = {
        "collection": "member_suspensions",
        "indexes": ["user", "organizational_unit", "-created_at"],
    }
