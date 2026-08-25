from django.http import JsonResponse
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import HealthCheckView


def root_status(request):
    """
    Root endpoint for Railway health verification.
    """
    return JsonResponse(
        {
            "status": "success",
            "message": "NDC Platform API is running",
            "version": "v1",
            "api_base": "/api/v1/",
            "documentation": "/api/docs/",
        }
    )


urlpatterns = [
    # Root endpoint
    path("", root_status, name="root-status"),
    # Health check
    path(
        "api/v1/health/",
        HealthCheckView.as_view(),
        name="health-check",
    ),
    # Monitoring
    path("", include("django_prometheus.urls")),
    # Authentication
    path(
        "api/v1/auth/",
        include("apps.accounts.urls"),
    ),
    # Organization hierarchy
    path(
        "api/v1/hierarchy/",
        include("apps.hierarchy.urls"),
    ),
    # Departments
    path(
        "api/v1/departments/",
        include("apps.departments.urls"),
    ),
    # Membership
    path(
        "api/v1/membership/",
        include("apps.membership.urls"),
    ),
    # Communication
    path(
        "api/v1/messaging/",
        include("apps.messaging.urls"),
    ),
    # Elections
    path(
        "api/v1/elections/",
        include("apps.elections.urls"),
    ),
    # In-person kiosk voting
    path(
        "api/v1/kiosk/",
        include("apps.kiosk.urls"),
    ),
    # Events
    path(
        "api/v1/events/",
        include("apps.events.urls"),
    ),
    # Finance
    path(
        "api/v1/finance/",
        include("apps.finance.urls"),
    ),
    # Dashboard
    path(
        "api/v1/dashboard/",
        include("apps.dashboard.urls"),
    ),
    # Welfare
    path(
        "api/v1/welfare/",
        include("apps.welfare.urls"),
    ),
    # Complaints
    path(
        "api/v1/complaints/",
        include("apps.complaints.urls"),
    ),
    # Documents
    path(
        "api/v1/documents/",
        include("apps.documents.urls"),
    ),
    # Donations
    path(
        "api/v1/donations/",
        include("apps.donations.urls"),
    ),
    # Volunteers
    path(
        "api/v1/volunteers/",
        include("apps.volunteers.urls"),
    ),
    # Analytics
    path(
        "api/v1/analytics/",
        include("apps.analytics.urls"),
    ),
    # Media
    path(
        "api/v1/media/",
        include("apps.media.urls"),
    ),
    # AI Chatbot
    path(
        "api/v1/chatbot/",
        include("apps.chatbot.urls"),
    ),
    # Discipline
    path(
        "api/v1/discipline/",
        include("apps.discipline.urls"),
    ),
    # Executive AI Assistant
    path(
        "api/v1/executive-ai/",
        include("apps.executive_ai.urls"),
    ),
    # Membership dues payment
    path(
        "api/v1/dues/",
        include("apps.dues.urls"),
    ),
    # Audit logs
    path(
        "api/v1/audit/",
        include("apps.core.urls"),
    ),
    # API Documentation
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
