from django.urls import path

from apps.volunteers.views import (
    MyVolunteerProfileView,
    VolunteerOpportunityDetailView,
    VolunteerOpportunityListCreateView,
    VolunteerSignupListView,
    VolunteerSignupView,
)

urlpatterns = [
    path("profile/", MyVolunteerProfileView.as_view(), name="my-volunteer-profile"),
    path(
        "opportunities/",
        VolunteerOpportunityListCreateView.as_view(),
        name="volunteer-opportunity-list-create",
    ),
    path(
        "opportunities/<str:opportunity_id>/",
        VolunteerOpportunityDetailView.as_view(),
        name="volunteer-opportunity-detail",
    ),
    path(
        "opportunities/<str:opportunity_id>/signup/",
        VolunteerSignupView.as_view(),
        name="volunteer-signup",
    ),
    path(
        "opportunities/<str:opportunity_id>/signups/",
        VolunteerSignupListView.as_view(),
        name="volunteer-signup-list",
    ),
]
