from django.urls import path

from apps.welfare.views import WelfareRequestDetailView, WelfareRequestListCreateView

urlpatterns = [
    path(
        "requests/",
        WelfareRequestListCreateView.as_view(),
        name="welfare-request-list-create",
    ),
    path(
        "requests/<str:request_id>/",
        WelfareRequestDetailView.as_view(),
        name="welfare-request-detail",
    ),
]
