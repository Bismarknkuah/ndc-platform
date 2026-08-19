from drf_spectacular.utils import extend_schema
from mongoengine.errors import (
    DoesNotExist,
    NotUniqueError,
    ValidationError as MongoValidationError,
)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.volunteers.documents import (
    VolunteerOpportunity,
    VolunteerProfile,
    VolunteerSignup,
)
from apps.volunteers.permissions import can_manage_opportunities
from apps.volunteers.serializers import (
    VolunteerOpportunitySerializer,
    VolunteerProfileSerializer,
    VolunteerSignupSerializer,
)


def _get_opportunity_or_404(opportunity_id):
    try:
        return VolunteerOpportunity.objects.get(id=opportunity_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Volunteer opportunity not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class MyVolunteerProfileView(APIView):
    """GET/PUT /api/v1/volunteers/profile/ - opt in and manage your own volunteer profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: VolunteerProfileSerializer}, tags=["volunteers"])
    def get(self, request):
        profile = VolunteerProfile.objects(user=request.user).first()
        if profile is None:
            raise APIError(
                "You have not opted in as a volunteer yet.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            )
        return Response(VolunteerProfileSerializer(profile).data)

    @extend_schema(
        request=VolunteerProfileSerializer,
        responses={200: VolunteerProfileSerializer},
        tags=["volunteers"],
    )
    def put(self, request):
        serializer = VolunteerProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = VolunteerProfile.objects(user=request.user).first()
        if profile is None:
            profile = VolunteerProfile.objects.create(
                user=request.user,
                skills=serializer.validated_data.get("skills", []),
                availability_notes=serializer.validated_data.get(
                    "availability_notes", ""
                ),
            )
        else:
            profile.skills = serializer.validated_data.get("skills", profile.skills)
            profile.availability_notes = serializer.validated_data.get(
                "availability_notes", profile.availability_notes
            )
            profile.is_active = serializer.validated_data.get(
                "is_active", profile.is_active
            )
            profile.save()
        return Response(VolunteerProfileSerializer(profile).data)


class VolunteerOpportunityListCreateView(APIView):
    """GET/POST /api/v1/volunteers/opportunities/?target_unit_id=&event_id=&status=&upcoming=true"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: VolunteerOpportunitySerializer(many=True)}, tags=["volunteers"]
    )
    def get(self, request):
        qs = VolunteerOpportunity.objects.all()
        target_unit_id = request.query_params.get("target_unit_id")
        if target_unit_id:
            qs = qs.filter(target_unit=target_unit_id)
        event_id = request.query_params.get("event_id")
        if event_id:
            qs = qs.filter(event=event_id)
        opportunity_status = request.query_params.get("status")
        if opportunity_status:
            qs = qs.filter(status=opportunity_status)
        if request.query_params.get("upcoming") == "true":
            import datetime

            qs = qs.filter(
                scheduled_start__gte=datetime.datetime.utcnow(), status="OPEN"
            )
        paginator, page = paginate_queryset(
            qs.order_by("scheduled_start"), request, self
        )
        return paginator.get_paginated_response(
            VolunteerOpportunitySerializer(page, many=True).data
        )

    @extend_schema(
        request=VolunteerOpportunitySerializer,
        responses={201: VolunteerOpportunitySerializer},
        tags=["volunteers"],
    )
    def post(self, request):
        serializer = VolunteerOpportunitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["target_unit_id"]
        if not can_manage_opportunities(request.user, target_unit):
            raise APIError(
                "You do not have authority to organize volunteer opportunities for this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        opportunity = VolunteerOpportunity.objects.create(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            event=serializer.validated_data.get("event_id"),
            target_unit=target_unit,
            organizer=request.user,
            needed_count=serializer.validated_data["needed_count"],
            location=serializer.validated_data.get("location", ""),
            scheduled_start=serializer.validated_data["scheduled_start"],
            scheduled_end=serializer.validated_data["scheduled_end"],
        )

        from apps.messaging.services import notify_many, users_in_subtree

        audience = [u for u in users_in_subtree(target_unit) if u.id != request.user.id]
        notify_many(
            audience,
            "EVENT",
            title=f"Volunteers needed: {opportunity.title}",
            body=opportunity.location,
            target=opportunity,
        )

        log_action(
            request.user,
            "volunteers.opportunity.create",
            request=request,
            target=opportunity,
            description=opportunity.title,
        )
        return Response(
            VolunteerOpportunitySerializer(opportunity).data,
            status=status.HTTP_201_CREATED,
        )


class VolunteerOpportunityDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: VolunteerOpportunitySerializer}, tags=["volunteers"])
    def get(self, request, opportunity_id):
        return Response(
            VolunteerOpportunitySerializer(_get_opportunity_or_404(opportunity_id)).data
        )

    @extend_schema(
        request=VolunteerOpportunitySerializer,
        responses={200: VolunteerOpportunitySerializer},
        tags=["volunteers"],
    )
    def patch(self, request, opportunity_id):
        opportunity = _get_opportunity_or_404(opportunity_id)
        if not can_manage_opportunities(request.user, opportunity.target_unit):
            raise APIError(
                "You do not have authority to modify this opportunity.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        for field in (
            "title",
            "description",
            "needed_count",
            "location",
            "status",
            "scheduled_start",
            "scheduled_end",
        ):
            if field in request.data:
                setattr(opportunity, field, request.data[field])
        opportunity.save()
        log_action(
            request.user,
            "volunteers.opportunity.update",
            request=request,
            target=opportunity,
            description=f"status={opportunity.status}",
        )
        return Response(VolunteerOpportunitySerializer(opportunity).data)


class VolunteerSignupView(APIView):
    """POST /api/v1/volunteers/opportunities/<id>/signup/ - sign up (auto-creates a volunteer profile if needed)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={201: VolunteerSignupSerializer}, tags=["volunteers"]
    )
    def post(self, request, opportunity_id):
        opportunity = _get_opportunity_or_404(opportunity_id)

        if VolunteerProfile.objects(user=request.user).first() is None:
            VolunteerProfile.objects.create(user=request.user)

        try:
            signup = VolunteerSignup.objects.create(
                opportunity=opportunity, volunteer=request.user
            )
        except NotUniqueError as exc:
            raise APIError(
                "You have already signed up for this opportunity.",
                code="conflict",
                http_status=status.HTTP_409_CONFLICT,
            ) from exc

        filled_count = VolunteerSignup.objects(
            opportunity=opportunity, status__in=["SIGNED_UP", "CONFIRMED"]
        ).count()
        if filled_count >= opportunity.needed_count:
            opportunity.status = "FILLED"
            opportunity.save()

        log_action(
            request.user,
            "volunteers.signup.create",
            request=request,
            target=opportunity,
        )
        return Response(
            VolunteerSignupSerializer(signup).data, status=status.HTTP_201_CREATED
        )


class VolunteerSignupListView(APIView):
    """GET /api/v1/volunteers/opportunities/<id>/signups/ - organizer views the roster."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: VolunteerSignupSerializer(many=True)}, tags=["volunteers"]
    )
    def get(self, request, opportunity_id):
        opportunity = _get_opportunity_or_404(opportunity_id)
        if not (
            request.user.is_superadmin
            or opportunity.organizer.id == request.user.id
            or can_manage_opportunities(request.user, opportunity.target_unit)
        ):
            raise APIError(
                "Only the organizer can view the volunteer roster.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        signups = VolunteerSignup.objects(opportunity=opportunity).order_by(
            "-signed_up_at"
        )
        return Response(VolunteerSignupSerializer(signups, many=True).data)
