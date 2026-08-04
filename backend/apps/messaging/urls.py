from django.urls import path

from apps.messaging.views_broadcasts import (
    BroadcastAcknowledgeView,
    BroadcastAcknowledgementsListView,
    BroadcastListCreateView,
)
from apps.messaging.views_direct import (
    DirectMessageListCreateView,
    DirectMessageMarkReadView,
)
from apps.messaging.views_groups import (
    DiscussionGroupListCreateView,
    DiscussionGroupMembersView,
    GroupMessageListCreateView,
)
from apps.messaging.views_meetings import (
    MeetingDetailView,
    MeetingListCreateView,
    MeetingRSVPListView,
    MeetingRSVPView,
)
from apps.messaging.views_minutes import MeetingMinutesView
from apps.messaging.views_notifications import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationPreferenceView,
    NotificationUnreadCountView,
)
from apps.messaging.views_reports import ReportDetailView, ReportListCreateView

urlpatterns = [
    # Broadcasts (directives / announcements)
    path(
        "broadcasts/", BroadcastListCreateView.as_view(), name="broadcast-list-create"
    ),
    path(
        "broadcasts/<str:broadcast_id>/acknowledge/",
        BroadcastAcknowledgeView.as_view(),
        name="broadcast-acknowledge",
    ),
    path(
        "broadcasts/<str:broadcast_id>/acknowledgements/",
        BroadcastAcknowledgementsListView.as_view(),
        name="broadcast-acknowledgements",
    ),
    # Upward reports
    path("reports/", ReportListCreateView.as_view(), name="report-list-create"),
    path("reports/<str:report_id>/", ReportDetailView.as_view(), name="report-detail"),
    # Discussion groups
    path("groups/", DiscussionGroupListCreateView.as_view(), name="group-list-create"),
    path(
        "groups/<str:group_id>/members/",
        DiscussionGroupMembersView.as_view(),
        name="group-members",
    ),
    path(
        "groups/<str:group_id>/messages/",
        GroupMessageListCreateView.as_view(),
        name="group-message-list-create",
    ),
    # Meetings & workshops
    path("meetings/", MeetingListCreateView.as_view(), name="meeting-list-create"),
    path(
        "meetings/<str:meeting_id>/", MeetingDetailView.as_view(), name="meeting-detail"
    ),
    path(
        "meetings/<str:meeting_id>/rsvp/",
        MeetingRSVPView.as_view(),
        name="meeting-rsvp",
    ),
    path(
        "meetings/<str:meeting_id>/rsvps/",
        MeetingRSVPListView.as_view(),
        name="meeting-rsvp-list",
    ),
    path(
        "meetings/<str:meeting_id>/minutes/",
        MeetingMinutesView.as_view(),
        name="meeting-minutes",
    ),
    # Direct messages
    path(
        "direct-messages/",
        DirectMessageListCreateView.as_view(),
        name="direct-message-list-create",
    ),
    path(
        "direct-messages/<str:message_id>/read/",
        DirectMessageMarkReadView.as_view(),
        name="direct-message-read",
    ),
    # Notifications
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/unread-count/",
        NotificationUnreadCountView.as_view(),
        name="notification-unread-count",
    ),
    path(
        "notifications/<str:notification_id>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-read",
    ),
    path(
        "notifications/mark-all-read/",
        NotificationMarkAllReadView.as_view(),
        name="notification-mark-all-read",
    ),
    path(
        "notification-preferences/",
        NotificationPreferenceView.as_view(),
        name="notification-preferences",
    ),
]
