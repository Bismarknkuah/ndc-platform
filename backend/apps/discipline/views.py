import datetime

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from mongoengine import Q
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.documents import User
from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.hierarchy.documents import OrganizationalUnit
from apps.discipline.documents import (
    DisciplinaryCase,
    DisciplinaryCommittee,
    MemberSuspension,
)
from apps.discipline.permissions import (
    can_deliberate_case,
    can_manage_discipline,
    can_view_case,
)
from apps.discipline.serializers import (
    CreateDisciplinaryCaseSerializer,
    CreateMemberSuspensionSerializer,
    DisciplinaryCaseSerializer,
    DisciplinaryCommitteeSerializer,
    ExecutiveDecisionSerializer,
    MemberSuspensionSerializer,
    RecommendationSerializer,
)


def _get_unit_or_400(unit_id, field_name="organizational_unit_id"):
    try:
        return OrganizationalUnit.objects.get(id=unit_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(f"Invalid {field_name}.", code="invalid_input") from exc


def _get_user_or_400(user_id, field_name="user_id"):
    try:
        return User.objects.get(id=user_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(f"Invalid {field_name}.", code="invalid_input") from exc


class DisciplinaryCommitteeListCreateView(APIView):
    """
    GET  /api/v1/discipline/committees/?organizational_unit_id=
    POST /api/v1/discipline/committees/ {organizational_unit_id, member_ids: [3 ids]}

    Article 46(5): a 3-member committee, elected by the Executives at that
    level, whose members must not themselves be Executives there - every
    level except the district (which has no Executive of its own to elect
    one, per Article 17/58's organogram).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("organizational_unit_id", str, required=True)],
        responses={200: DisciplinaryCommitteeSerializer(many=True)},
        tags=["discipline"],
    )
    def get(self, request):
        unit_id = request.query_params.get("organizational_unit_id")
        if not unit_id:
            raise APIError("organizational_unit_id is required.", code="invalid_input")
        unit = _get_unit_or_400(unit_id)
        qs = DisciplinaryCommittee.objects(organizational_unit=unit, is_active=True)
        return Response(DisciplinaryCommitteeSerializer(qs, many=True).data)

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={201: DisciplinaryCommitteeSerializer},
        tags=["discipline"],
    )
    def post(self, request):
        unit_id = request.data.get("organizational_unit_id")
        member_ids = request.data.get("member_ids") or []
        if not unit_id:
            raise APIError("organizational_unit_id is required.", code="invalid_input")
        unit = _get_unit_or_400(unit_id)

        if unit.unit_type == "DISTRICT_COORDINATING_COMMITTEE":
            raise APIError(
                "Article 46(5): every level except the district has a "
                "Disciplinary Committee - a District Co-ordinating Committee "
                "has no Executive of its own to elect one.",
                code="invalid_level",
            )
        if not can_manage_discipline(request.user, unit):
            raise APIError(
                "You don't have authority to elect a Disciplinary Committee here.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if len(member_ids) != 3:
            raise APIError(
                "A Disciplinary Committee has exactly 3 members (Article 46(5)).",
                code="invalid_input",
            )

        members = [_get_user_or_400(uid) for uid in member_ids]
        for member in members:
            if (
                member.role
                and member.role.is_executive
                and member.organizational_unit
                and str(member.organizational_unit.id) == str(unit.id)
            ):
                raise APIError(
                    f"{member.full_name} holds an executive position at this unit and "
                    "cannot sit on its Disciplinary Committee (Article 46(5)).",
                    code="invalid_input",
                )

        existing = DisciplinaryCommittee.objects(organizational_unit=unit).first()
        if existing:
            existing.members = members
            existing.elected_at = datetime.datetime.utcnow()
            existing.is_active = True
            existing.save()
            committee = existing
        else:
            committee = DisciplinaryCommittee.objects.create(
                organizational_unit=unit, members=members
            )

        log_action(
            request.user,
            "discipline.committee.elect",
            request=request,
            target=committee,
            description=f"{unit.name}",
        )
        return Response(
            DisciplinaryCommitteeSerializer(committee).data,
            status=status.HTTP_201_CREATED,
        )


class DisciplinaryCaseListCreateView(APIView):
    """
    GET  /api/v1/discipline/cases/ - cases the caller reported, is the
         respondent of, sits on the committee for, or has executive
         authority over (via organizational_unit_id filter).
    POST /api/v1/discipline/cases/ - report a member for discipline
         (Article 46(8)). Any member may report; the case is
         automatically attached to the active Disciplinary Committee (if
         one has been elected) at the given unit.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("organizational_unit_id", str, required=False),
            OpenApiParameter("mine", bool, required=False),
        ],
        responses={200: DisciplinaryCaseSerializer(many=True)},
        tags=["discipline"],
    )
    def get(self, request):
        unit_id = request.query_params.get("organizational_unit_id")
        mine_only = request.query_params.get("mine") == "true"

        if mine_only:
            qs = DisciplinaryCase.objects(
                Q(respondent=request.user) | Q(reported_by=request.user),
                is_active=True,
            ).order_by("-created_at")
        elif unit_id:
            unit = _get_unit_or_400(unit_id)
            if not can_manage_discipline(request.user, unit):
                raise APIError(
                    "You don't have authority over this unit's cases.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            qs = DisciplinaryCase.objects(
                organizational_unit=unit, is_active=True
            ).order_by("-created_at")
        else:
            qs = DisciplinaryCase.objects(
                respondent=request.user, is_active=True
            ).order_by("-created_at")

        paginator, page = paginate_queryset(qs, request, self)
        return paginator.get_paginated_response(
            DisciplinaryCaseSerializer(page, many=True).data
        )

    @extend_schema(
        request=CreateDisciplinaryCaseSerializer,
        responses={201: DisciplinaryCaseSerializer},
        tags=["discipline"],
    )
    def post(self, request):
        serializer = CreateDisciplinaryCaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        unit = _get_unit_or_400(data["organizational_unit_id"])
        respondent = _get_user_or_400(data["respondent_id"], "respondent_id")
        committee = DisciplinaryCommittee.objects(
            organizational_unit=unit, is_active=True
        ).first()

        case = DisciplinaryCase.objects.create(
            organizational_unit=unit,
            committee=committee,
            respondent=respondent,
            reported_by=request.user,
            grounds=data["grounds"],
            description=data["description"],
        )
        log_action(
            request.user,
            "discipline.case.report",
            request=request,
            target=case,
            description=f"against {respondent.full_name}",
        )
        return Response(
            DisciplinaryCaseSerializer(case).data, status=status.HTTP_201_CREATED
        )


class DisciplinaryCaseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_case(self, request, case_id):
        try:
            case = DisciplinaryCase.objects.get(id=case_id, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Case not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if not can_view_case(request.user, case):
            raise APIError(
                "You don't have access to this case.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return case

    @extend_schema(responses={200: DisciplinaryCaseSerializer}, tags=["discipline"])
    def get(self, request, case_id):
        case = self._get_case(request, case_id)
        return Response(DisciplinaryCaseSerializer(case).data)


class DisciplinaryCaseConveneView(APIView):
    """POST /cases/<id>/convene/ - Article 47(3): the committee must convene
    within 14 days of receiving the complaint (surfaced client-side via
    `convene_overdue` on the case; not blocked server-side, since a late
    convening is still a real convening, just a flagged breach)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: DisciplinaryCaseSerializer}, tags=["discipline"]
    )
    def post(self, request, case_id):
        try:
            case = DisciplinaryCase.objects.get(id=case_id, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Case not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if not can_deliberate_case(request.user, case):
            raise APIError(
                "Only the assigned Disciplinary Committee may convene this case.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if case.convened_at is not None:
            raise APIError("This case has already been convened.", code="invalid_state")

        case.convened_at = datetime.datetime.utcnow()
        case.status = "CONVENED"
        case.save()
        log_action(
            request.user, "discipline.case.convene", request=request, target=case
        )
        return Response(DisciplinaryCaseSerializer(case).data)


class DisciplinaryCaseRecommendView(APIView):
    """POST /cases/<id>/recommend/ - the committee's recommendation
    (Article 47(4)/(5)): majority decision, transmitted to the Executive
    Committee for a final decision."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RecommendationSerializer,
        responses={200: DisciplinaryCaseSerializer},
        tags=["discipline"],
    )
    def post(self, request, case_id):
        try:
            case = DisciplinaryCase.objects.get(id=case_id, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Case not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if not can_deliberate_case(request.user, case):
            raise APIError(
                "Only the assigned Disciplinary Committee may record a recommendation.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if case.convened_at is None:
            raise APIError(
                "The committee must convene before recommending.", code="invalid_state"
            )

        serializer = RecommendationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case.recommendation = serializer.validated_data["recommendation"]
        case.recommended_measure = serializer.validated_data["recommended_measure"]
        case.recommended_at = datetime.datetime.utcnow()
        case.status = "RECOMMENDED"
        case.save()
        log_action(
            request.user, "discipline.case.recommend", request=request, target=case
        )
        return Response(DisciplinaryCaseSerializer(case).data)


class DisciplinaryCaseDecideView(APIView):
    """POST /cases/<id>/decide/ - the Executive Committee's final decision
    (Article 47(9)): varying the committee's recommendation requires a
    2/3 majority of the Executive Committee. This platform cannot verify
    a real-world vote count, so `confirmed_two_thirds_majority` must be
    explicitly sent as true when the final measure differs from the
    recommended one - a deliberate confirmation step rather than a
    silent override."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ExecutiveDecisionSerializer,
        responses={200: DisciplinaryCaseSerializer},
        tags=["discipline"],
    )
    def post(self, request, case_id):
        try:
            case = DisciplinaryCase.objects.get(id=case_id, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Case not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if not can_manage_discipline(request.user, case.organizational_unit):
            raise APIError(
                "You don't have Executive Committee authority over this case.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if case.recommended_measure is None:
            raise APIError(
                "The committee must record a recommendation before a decision can be made.",
                code="invalid_state",
            )

        serializer = ExecutiveDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        varies = data["final_measure"] != case.recommended_measure

        if varies and not request.data.get("confirmed_two_thirds_majority"):
            raise APIError(
                "Varying the committee's recommendation requires a 2/3 majority "
                "of the Executive Committee (Article 47(9)). Resubmit with "
                "confirmed_two_thirds_majority: true once that vote has been taken.",
                code="confirmation_required",
            )

        case.final_decision = data["final_decision"]
        case.final_measure = data["final_measure"]
        case.varied_from_recommendation = varies
        case.decided_at = datetime.datetime.utcnow()
        case.decided_by = request.user
        case.status = "DECIDED"
        case.save()
        log_action(request.user, "discipline.case.decide", request=request, target=case)
        return Response(DisciplinaryCaseSerializer(case).data)


class DisciplinaryCaseAppealView(APIView):
    """POST /cases/<id>/appeal/ - Article 47(6): the respondent may appeal
    within 14 days to the Executive Committee of the immediate higher
    level. Modeled as a new case at the parent unit, linked back via
    `parent_case`, since an appellate committee follows "the provisions
    of Articles 45 and 46" - i.e. the same process, one level up."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={201: DisciplinaryCaseSerializer},
        tags=["discipline"],
    )
    def post(self, request, case_id):
        try:
            case = DisciplinaryCase.objects.get(id=case_id, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Case not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if (
            str(case.respondent.id) != str(request.user.id)
            and not request.user.is_superadmin
        ):
            raise APIError(
                "Only the respondent may appeal this case.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if case.status != "DECIDED":
            raise APIError("Only a decided case may be appealed.", code="invalid_state")
        if case.organizational_unit.parent is None:
            raise APIError(
                "This case is already at the National level - the National "
                "Executive Committee's decision is final (Article 46(11)(a)).",
                code="invalid_state",
            )

        parent_unit = case.organizational_unit.parent
        parent_committee = DisciplinaryCommittee.objects(
            organizational_unit=parent_unit, is_active=True
        ).first()
        appeal_case = DisciplinaryCase.objects.create(
            organizational_unit=parent_unit,
            committee=parent_committee,
            respondent=case.respondent,
            reported_by=request.user,
            grounds=case.grounds,
            description=request.data.get("grounds_for_appeal", case.description),
            parent_case=case,
        )
        case.status = "APPEALED"
        case.save()

        log_action(
            request.user, "discipline.case.appeal", request=request, target=appeal_case
        )
        return Response(
            DisciplinaryCaseSerializer(appeal_case).data, status=status.HTTP_201_CREATED
        )


class MemberSuspensionListCreateView(APIView):
    """
    GET  /api/v1/discipline/suspensions/?organizational_unit_id=
    POST /api/v1/discipline/suspensions/ {user_id, reason} - Article
         46(1): the Executive Committee may suspend a member for up to
         six months BEFORE disciplinary proceedings begin, if considered
         in the Party's interest.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("organizational_unit_id", str, required=False)],
        responses={200: MemberSuspensionSerializer(many=True)},
        tags=["discipline"],
    )
    def get(self, request):
        unit_id = request.query_params.get("organizational_unit_id")
        if unit_id:
            unit = _get_unit_or_400(unit_id)
            if not can_manage_discipline(request.user, unit):
                raise APIError(
                    "You don't have authority over this unit's suspensions.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            qs = MemberSuspension.objects(organizational_unit=unit).order_by(
                "-created_at"
            )
        else:
            qs = MemberSuspension.objects(user=request.user).order_by("-created_at")
        paginator, page = paginate_queryset(qs, request, self)
        return paginator.get_paginated_response(
            MemberSuspensionSerializer(page, many=True).data
        )

    @extend_schema(
        request=CreateMemberSuspensionSerializer,
        responses={201: MemberSuspensionSerializer},
        tags=["discipline"],
    )
    def post(self, request):
        serializer = CreateMemberSuspensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        target_user = _get_user_or_400(data["user_id"])

        if target_user.organizational_unit is None:
            raise APIError(
                "This member has no organizational unit on record.",
                code="invalid_input",
            )
        if not can_manage_discipline(request.user, target_user.organizational_unit):
            raise APIError(
                "You don't have Executive Committee authority over this member.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        suspension = MemberSuspension.objects.create(
            user=target_user,
            organizational_unit=target_user.organizational_unit,
            suspended_by=request.user,
            reason=data["reason"],
        )
        log_action(
            request.user,
            "discipline.suspension.impose",
            request=request,
            target=suspension,
            description=f"{target_user.full_name}",
        )
        return Response(
            MemberSuspensionSerializer(suspension).data, status=status.HTTP_201_CREATED
        )


class MemberSuspensionReferView(APIView):
    """POST /suspensions/<id>/refer/ {case_id} - Article 46(2): refer the
    suspended member's matter to the Disciplinary Committee within one
    month, or the suspension lapses (enforced client-visibly via
    `referral_overdue`, not silently auto-lapsed server-side - an
    Executive Committee's failure to act shouldn't quietly erase the
    suspension without anyone noticing)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: MemberSuspensionSerializer},
        tags=["discipline"],
    )
    def post(self, request, suspension_id):
        try:
            suspension = MemberSuspension.objects.get(id=suspension_id)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Suspension not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if not can_manage_discipline(request.user, suspension.organizational_unit):
            raise APIError(
                "You don't have authority over this suspension.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        case_id = request.data.get("case_id")
        if not case_id:
            raise APIError("case_id is required.", code="invalid_input")
        try:
            case = DisciplinaryCase.objects.get(id=case_id)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError("Invalid case_id.", code="invalid_input") from exc

        suspension.related_case = case
        suspension.referred_at = datetime.datetime.utcnow()
        suspension.status = "REFERRED"
        suspension.save()
        log_action(
            request.user,
            "discipline.suspension.refer",
            request=request,
            target=suspension,
        )
        return Response(MemberSuspensionSerializer(suspension).data)


class MemberSuspensionRenewView(APIView):
    """POST /suspensions/<id>/renew/ - Article 46(4): renewable once, for
    up to five further consecutive months."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: MemberSuspensionSerializer}, tags=["discipline"]
    )
    def post(self, request, suspension_id):
        try:
            suspension = MemberSuspension.objects.get(id=suspension_id)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Suspension not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if not can_manage_discipline(request.user, suspension.organizational_unit):
            raise APIError(
                "You don't have authority over this suspension.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if suspension.renewal_count >= 1:
            raise APIError(
                "Article 46(4): a suspension may be renewed once only.",
                code="invalid_state",
            )

        suspension.renewal_count += 1
        suspension.renewed_at = datetime.datetime.utcnow()
        suspension.save()
        log_action(
            request.user,
            "discipline.suspension.renew",
            request=request,
            target=suspension,
        )
        return Response(MemberSuspensionSerializer(suspension).data)


class MemberSuspensionEndView(APIView):
    """POST /suspensions/<id>/end/ - end a suspension (case resolved,
    cleared, or the member reinstated)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: MemberSuspensionSerializer}, tags=["discipline"]
    )
    def post(self, request, suspension_id):
        try:
            suspension = MemberSuspension.objects.get(id=suspension_id)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Suspension not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if not can_manage_discipline(request.user, suspension.organizational_unit):
            raise APIError(
                "You don't have authority over this suspension.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        suspension.status = "ENDED"
        suspension.save()
        log_action(
            request.user,
            "discipline.suspension.end",
            request=request,
            target=suspension,
        )
        return Response(MemberSuspensionSerializer(suspension).data)
