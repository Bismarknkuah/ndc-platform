from django.urls import path

from apps.donations.views import (
    CampaignDetailView,
    CampaignListCreateView,
    CampaignProgressView,
    PledgeFulfillView,
    PledgeListCreateView,
)

urlpatterns = [
    path(
        "campaigns/",
        CampaignListCreateView.as_view(),
        name="donation-campaign-list-create",
    ),
    path(
        "campaigns/<str:campaign_id>/",
        CampaignDetailView.as_view(),
        name="donation-campaign-detail",
    ),
    path(
        "campaigns/<str:campaign_id>/progress/",
        CampaignProgressView.as_view(),
        name="donation-campaign-progress",
    ),
    path("pledges/", PledgeListCreateView.as_view(), name="pledge-list-create"),
    path(
        "pledges/<str:pledge_id>/fulfill/",
        PledgeFulfillView.as_view(),
        name="pledge-fulfill",
    ),
]
