from django.urls import path

from apps.analytics.ai_views import AIReportListCreateView
from apps.analytics.views import (
    DepartmentAnalyticsView,
    GISMapView,
    MembershipAnalyticsView,
)

urlpatterns = [
    path("membership/", MembershipAnalyticsView.as_view(), name="analytics-membership"),
    path(
        "departments/", DepartmentAnalyticsView.as_view(), name="analytics-departments"
    ),
    path("map/", GISMapView.as_view(), name="analytics-map"),
    path("ai-report/", AIReportListCreateView.as_view(), name="analytics-ai-report"),
]
