from decimal import Decimal

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.donations.documents import FundraisingCampaign, Pledge
from apps.donations.permissions import can_manage_campaign
from apps.donations.serializers import (
    FulfillPledgeSerializer,
    FundraisingCampaignSerializer,
    PledgeSerializer,
)


def _get_campaign_or_404(campaign_id):
    try:
        return FundraisingCampaign.objects.get(id=campaign_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Campaign not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


def _get_pledge_or_404(pledge_id):
    try:
        return Pledge.objects.get(id=pledge_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Pledge not found.", code="not_found", http_status=status.HTTP_404_NOT_FOUND
        ) from exc


class CampaignListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: FundraisingCampaignSerializer(many=True)}, tags=["donations"]
    )
    def get(self, request):
        qs = FundraisingCampaign.objects.all()
        target_unit_id = request.query_params.get("target_unit_id")
        if target_unit_id:
            qs = qs.filter(target_unit=target_unit_id)
        campaign_status = request.query_params.get("status")
        if campaign_status:
            qs = qs.filter(status=campaign_status)
        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            FundraisingCampaignSerializer(page, many=True).data
        )

    @extend_schema(
        request=FundraisingCampaignSerializer,
        responses={201: FundraisingCampaignSerializer},
        tags=["donations"],
    )
    def post(self, request):
        serializer = FundraisingCampaignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["target_unit_id"]
        if not can_manage_campaign(request.user, target_unit):
            raise APIError(
                "You do not have authority to organize a fundraising campaign for this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        campaign = FundraisingCampaign.objects.create(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            target_unit=target_unit,
            organized_by=request.user,
            goal_amount=serializer.validated_data["goal_amount"],
            currency=serializer.validated_data.get("currency", "GHS"),
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data["end_date"],
        )
        log_action(
            request.user,
            "donations.campaign.create",
            request=request,
            target=campaign,
            description=campaign.title,
        )
        return Response(
            FundraisingCampaignSerializer(campaign).data, status=status.HTTP_201_CREATED
        )


class CampaignDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: FundraisingCampaignSerializer}, tags=["donations"])
    def get(self, request, campaign_id):
        return Response(
            FundraisingCampaignSerializer(_get_campaign_or_404(campaign_id)).data
        )

    @extend_schema(
        request=FundraisingCampaignSerializer,
        responses={200: FundraisingCampaignSerializer},
        tags=["donations"],
    )
    def patch(self, request, campaign_id):
        campaign = _get_campaign_or_404(campaign_id)
        if not can_manage_campaign(request.user, campaign.target_unit):
            raise APIError(
                "You do not have authority to modify this campaign.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        for field in ("title", "description", "status", "start_date", "end_date"):
            if field in request.data:
                setattr(campaign, field, request.data[field])
        campaign.save()
        log_action(
            request.user,
            "donations.campaign.update",
            request=request,
            target=campaign,
            description=f"status={campaign.status}",
        )
        return Response(FundraisingCampaignSerializer(campaign).data)


class CampaignProgressView(APIView):
    """GET /api/v1/donations/campaigns/<id>/progress/ - goal vs pledged vs fulfilled."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["donations"])
    def get(self, request, campaign_id):
        campaign = _get_campaign_or_404(campaign_id)
        pledges = list(Pledge.objects(campaign=campaign).filter(status__ne="CANCELLED"))
        total_pledged = sum((p.pledged_amount for p in pledges), start=Decimal("0"))
        total_fulfilled = sum((p.fulfilled_amount for p in pledges), start=Decimal("0"))
        return Response(
            {
                "campaign_id": str(campaign.id),
                "goal_amount": str(campaign.goal_amount),
                "total_pledged": str(total_pledged),
                "total_fulfilled": str(total_fulfilled),
                "pledge_count": len(pledges),
                "percentage_of_goal_fulfilled": (
                    round(float(total_fulfilled / campaign.goal_amount) * 100, 2)
                    if campaign.goal_amount
                    else 0.0
                ),
            }
        )


class PledgeListCreateView(APIView):
    """
    GET  /api/v1/donations/pledges/?campaign_id=
    POST /api/v1/donations/pledges/ - a member pledges for themselves
         (donor_user_id omitted defaults to self), or campaign authority
         records a pledge on behalf of an external supporter.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PledgeSerializer(many=True)}, tags=["donations"])
    def get(self, request):
        qs = Pledge.objects.all()
        campaign_id = request.query_params.get("campaign_id")
        if campaign_id:
            qs = qs.filter(campaign=campaign_id)
        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(PledgeSerializer(page, many=True).data)

    @extend_schema(
        request=PledgeSerializer, responses={201: PledgeSerializer}, tags=["donations"]
    )
    def post(self, request):
        serializer = PledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = serializer.validated_data["campaign_id"]
        donor_user = serializer.validated_data.get("donor_user_id")

        is_self_pledge = donor_user is None or donor_user.id == request.user.id
        if not is_self_pledge and not can_manage_campaign(
            request.user, campaign.target_unit
        ):
            raise APIError(
                "Only campaign authority can record a pledge on someone else's behalf.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        donor_name = serializer.validated_data.get("donor_name")
        if donor_user is None and not donor_name:
            donor_user = request.user  # self-pledge default

        pledge = Pledge.objects.create(
            campaign=campaign,
            donor_user=donor_user,
            donor_name=donor_name,
            donor_contact=serializer.validated_data.get("donor_contact"),
            pledged_amount=serializer.validated_data["pledged_amount"],
            recorded_by=request.user,
        )
        log_action(
            request.user,
            "donations.pledge.create",
            request=request,
            target=pledge,
            description=pledge.donor_display_name,
        )
        return Response(PledgeSerializer(pledge).data, status=status.HTTP_201_CREATED)


class PledgeFulfillView(APIView):
    """
    POST /api/v1/donations/pledges/<id>/fulfill/ {"amount": "..."}
    Records an actual payment received against a pledge (full or
    partial) and automatically creates a matching FinanceRecord income
    entry - campaign authority only.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=FulfillPledgeSerializer,
        responses={200: PledgeSerializer},
        tags=["donations"],
    )
    def post(self, request, pledge_id):
        pledge = _get_pledge_or_404(pledge_id)
        if not can_manage_campaign(request.user, pledge.campaign.target_unit):
            raise APIError(
                "Only campaign authority can record a fulfillment.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        serializer = FulfillPledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        remaining = pledge.pledged_amount - pledge.fulfilled_amount
        if amount > remaining:
            raise APIError(
                f"Amount exceeds the remaining pledge balance ({remaining}).",
                code="invalid_amount",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.finance.documents import FinanceRecord

        finance_record = FinanceRecord.objects.create(
            record_type="INCOME",
            category="Fundraising Event",
            amount=amount,
            currency=pledge.campaign.currency,
            description=f"Pledge fulfillment from {pledge.donor_display_name} - {pledge.campaign.title}",
            organizational_unit=pledge.campaign.target_unit,
            recorded_by=request.user,
            status="APPROVED",
        )
        import datetime

        finance_record.approved_by = request.user
        finance_record.approved_at = datetime.datetime.utcnow()
        finance_record.save()

        pledge.fulfilled_amount += amount
        pledge.finance_records.append(finance_record)
        pledge.status = (
            "FULFILLED"
            if pledge.fulfilled_amount >= pledge.pledged_amount
            else "PARTIALLY_FULFILLED"
        )
        pledge.save()

        log_action(
            request.user,
            "donations.pledge.fulfill",
            request=request,
            target=pledge,
            description=f"amount={amount}",
        )
        return Response(PledgeSerializer(pledge).data)
