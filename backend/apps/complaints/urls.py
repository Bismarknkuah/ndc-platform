from django.urls import path

from apps.complaints.views import (
    ComplaintDetailView,
    ComplaintListCreateView,
    PetitionSupportView,
)

urlpatterns = [
    path("", ComplaintListCreateView.as_view(), name="complaint-list-create"),
    path("<str:complaint_id>/", ComplaintDetailView.as_view(), name="complaint-detail"),
    path(
        "<str:complaint_id>/support/",
        PetitionSupportView.as_view(),
        name="petition-support",
    ),
]
