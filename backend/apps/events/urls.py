from django.urls import path

from apps.events.views import (
    CampaignDetailView,
    CampaignListCreateView,
    EventDetailView,
    EventListCreateView,
    EventRSVPListView,
    EventRSVPView,
)

urlpatterns = [
    path("campaigns/", CampaignListCreateView.as_view(), name="campaign-list-create"),
    path(
        "campaigns/<str:campaign_id>/",
        CampaignDetailView.as_view(),
        name="campaign-detail",
    ),
    path("", EventListCreateView.as_view(), name="event-list-create"),
    path("<str:event_id>/", EventDetailView.as_view(), name="event-detail"),
    path("<str:event_id>/rsvp/", EventRSVPView.as_view(), name="event-rsvp"),
    path("<str:event_id>/rsvps/", EventRSVPListView.as_view(), name="event-rsvp-list"),
]
