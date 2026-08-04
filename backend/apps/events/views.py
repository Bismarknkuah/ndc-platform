from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.events.documents import Campaign, Event, EventRSVP
from apps.events.permissions import can_manage_events
from apps.events.serializers import (
    CampaignSerializer,
    EventRSVPRecordSerializer,
    EventRSVPSerializer,
    EventSerializer,
)


def _get_campaign_or_404(campaign_id):
    try:
        return Campaign.objects.get(id=campaign_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Campaign not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


def _get_event_or_404(event_id):
    try:
        return Event.objects.get(id=event_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Event not found.", code="not_found", http_status=status.HTTP_404_NOT_FOUND
        ) from exc


class CampaignListCreateView(APIView):
    """GET/POST /api/v1/events/campaigns/?target_unit_id=&status="""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CampaignSerializer(many=True)}, tags=["events"])
    def get(self, request):
        qs = Campaign.objects.all()
        target_unit_id = request.query_params.get("target_unit_id")
        if target_unit_id:
            qs = qs.filter(target_unit=target_unit_id)
        campaign_status = request.query_params.get("status")
        if campaign_status:
            qs = qs.filter(status=campaign_status)
        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            CampaignSerializer(page, many=True).data
        )

    @extend_schema(
        request=CampaignSerializer, responses={201: CampaignSerializer}, tags=["events"]
    )
    def post(self, request):
        serializer = CampaignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["target_unit_id"]
        if not can_manage_events(request.user, target_unit):
            raise APIError(
                "You do not have authority to organize a campaign for this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        campaign = Campaign.objects.create(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            goal_description=serializer.validated_data.get("goal_description", ""),
            target_unit=target_unit,
            organized_by=request.user,
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data["end_date"],
        )
        log_action(
            request.user,
            "events.campaign.create",
            request=request,
            target=campaign,
            description=campaign.title,
        )
        return Response(
            CampaignSerializer(campaign).data, status=status.HTTP_201_CREATED
        )


class CampaignDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CampaignSerializer}, tags=["events"])
    def get(self, request, campaign_id):
        return Response(CampaignSerializer(_get_campaign_or_404(campaign_id)).data)

    @extend_schema(
        request=CampaignSerializer, responses={200: CampaignSerializer}, tags=["events"]
    )
    def patch(self, request, campaign_id):
        campaign = _get_campaign_or_404(campaign_id)
        if not can_manage_events(request.user, campaign.target_unit):
            raise APIError(
                "You do not have authority to modify this campaign.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        for field in (
            "title",
            "description",
            "goal_description",
            "status",
            "start_date",
            "end_date",
        ):
            if field in request.data:
                setattr(campaign, field, request.data[field])
        campaign.save()
        log_action(
            request.user,
            "events.campaign.update",
            request=request,
            target=campaign,
            description=f"status={campaign.status}",
        )
        return Response(CampaignSerializer(campaign).data)


class EventListCreateView(APIView):
    """GET/POST /api/v1/events/?target_unit_id=&campaign_id=&status=&upcoming=true"""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: EventSerializer(many=True)}, tags=["events"])
    def get(self, request):
        qs = Event.objects.all()
        target_unit_id = request.query_params.get("target_unit_id")
        if target_unit_id:
            qs = qs.filter(target_unit=target_unit_id)
        campaign_id = request.query_params.get("campaign_id")
        if campaign_id:
            qs = qs.filter(campaign=campaign_id)
        event_status = request.query_params.get("status")
        if event_status:
            qs = qs.filter(status=event_status)
        if request.query_params.get("upcoming") == "true":
            import datetime

            qs = qs.filter(
                scheduled_start__gte=datetime.datetime.utcnow(), status="SCHEDULED"
            )
        paginator, page = paginate_queryset(
            qs.order_by("scheduled_start"), request, self
        )
        return paginator.get_paginated_response(EventSerializer(page, many=True).data)

    @extend_schema(
        request=EventSerializer, responses={201: EventSerializer}, tags=["events"]
    )
    def post(self, request):
        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["target_unit_id"]
        if not can_manage_events(request.user, target_unit):
            raise APIError(
                "You do not have authority to organize an event for this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        event = Event.objects.create(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            event_type=serializer.validated_data["event_type"],
            campaign=serializer.validated_data.get("campaign_id"),
            target_unit=target_unit,
            organizer=request.user,
            location=serializer.validated_data.get("location", ""),
            scheduled_start=serializer.validated_data["scheduled_start"],
            scheduled_end=serializer.validated_data["scheduled_end"],
        )

        from apps.messaging.services import notify_many, users_in_subtree

        audience = [u for u in users_in_subtree(target_unit) if u.id != request.user.id]
        notify_many(
            audience,
            "EVENT",
            title=f"New event: {event.title}",
            body=event.location,
            target=event,
        )

        log_action(
            request.user,
            "events.event.create",
            request=request,
            target=event,
            description=event.title,
        )
        return Response(EventSerializer(event).data, status=status.HTTP_201_CREATED)


class EventDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: EventSerializer}, tags=["events"])
    def get(self, request, event_id):
        return Response(EventSerializer(_get_event_or_404(event_id)).data)

    @extend_schema(
        request=EventSerializer, responses={200: EventSerializer}, tags=["events"]
    )
    def patch(self, request, event_id):
        event = _get_event_or_404(event_id)
        if not can_manage_events(request.user, event.target_unit):
            raise APIError(
                "You do not have authority to modify this event.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        for field in (
            "title",
            "description",
            "location",
            "status",
            "scheduled_start",
            "scheduled_end",
        ):
            if field in request.data:
                setattr(event, field, request.data[field])
        event.save()
        log_action(
            request.user,
            "events.event.update",
            request=request,
            target=event,
            description=f"status={event.status}",
        )
        return Response(EventSerializer(event).data)


class EventRSVPView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=EventRSVPSerializer,
        responses={201: EventRSVPRecordSerializer},
        tags=["events"],
    )
    def post(self, request, event_id):
        event = _get_event_or_404(event_id)
        serializer = EventRSVPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rsvp = EventRSVP.objects(event=event, user=request.user).first()
        if rsvp is None:
            rsvp = EventRSVP.objects.create(
                event=event,
                user=request.user,
                status=serializer.validated_data["status"],
            )
        else:
            rsvp.status = serializer.validated_data["status"]
            import datetime

            rsvp.responded_at = datetime.datetime.utcnow()
            rsvp.save()
        return Response(
            EventRSVPRecordSerializer(rsvp).data, status=status.HTTP_201_CREATED
        )


class EventRSVPListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: EventRSVPRecordSerializer(many=True)}, tags=["events"]
    )
    def get(self, request, event_id):
        event = _get_event_or_404(event_id)
        if not (
            request.user.is_superadmin
            or event.organizer.id == request.user.id
            or can_manage_events(request.user, event.target_unit)
        ):
            raise APIError(
                "Only the organizer can view the RSVP list.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        rsvps = EventRSVP.objects(event=event).order_by("-responded_at")
        return Response(
            {
                "attending_count": rsvps.filter(status="ATTENDING").count(),
                "declined_count": rsvps.filter(status="DECLINED").count(),
                "rsvps": EventRSVPRecordSerializer(rsvps, many=True).data,
            }
        )
