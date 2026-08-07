from django.urls import path

from apps.executive_ai.views import (
    DraftBroadcastView,
    GenerateMeetingAgendaView,
    GroundBriefingView,
    SummarizePendingItemsView,
)

urlpatterns = [
    path(
        "draft-broadcast/",
        DraftBroadcastView.as_view(),
        name="executive-ai-draft-broadcast",
    ),
    path(
        "summarize-pending/",
        SummarizePendingItemsView.as_view(),
        name="executive-ai-summarize-pending",
    ),
    path(
        "meeting-agenda/",
        GenerateMeetingAgendaView.as_view(),
        name="executive-ai-meeting-agenda",
    ),
    path(
        "ground-briefing/<str:unit_id>/",
        GroundBriefingView.as_view(),
        name="executive-ai-ground-briefing",
    ),
]
