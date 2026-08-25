from django.urls import path

from apps.elections.views_agents import (
    PollingAgentAssignmentListCreateView,
    PollingAgentCheckInView,
)
from apps.elections.views_elections import (
    CandidateListCreateView,
    ElectionDetailView,
    ElectionListCreateView,
)
from apps.elections.views_requests import (
    ElectionRequestDetailView,
    ElectionRequestListCreateView,
)
from apps.kiosk.views import KioskRegistrationView
from apps.elections.views_results import (
    ResultSubmissionDetailView,
    ResultSubmissionListCreateView,
    ResultSummaryView,
)
from apps.elections.views_voting import (
    CastVoteView,
    EligibleVoterDetailView,
    EligibleVoterListCreateView,
    MyEligibilityView,
)

urlpatterns = [
    path("", ElectionListCreateView.as_view(), name="election-list-create"),
    path(
        "results/",
        ResultSubmissionListCreateView.as_view(),
        name="election-result-list-create",
    ),
    path(
        "results/<str:submission_id>/",
        ResultSubmissionDetailView.as_view(),
        name="election-result-detail",
    ),
    path(
        "agents/",
        PollingAgentAssignmentListCreateView.as_view(),
        name="election-agent-list-create",
    ),
    path(
        "agents/<str:assignment_id>/check-in/",
        PollingAgentCheckInView.as_view(),
        name="election-agent-check-in",
    ),
    path(
        "requests/",
        ElectionRequestListCreateView.as_view(),
        name="election-request-list-create",
    ),
    path(
        "requests/<str:request_id>/",
        ElectionRequestDetailView.as_view(),
        name="election-request-detail",
    ),
    path("<str:election_id>/", ElectionDetailView.as_view(), name="election-detail"),
    path(
        "<str:election_id>/candidates/",
        CandidateListCreateView.as_view(),
        name="election-candidate-list-create",
    ),
    path(
        "<str:election_id>/results/summary/",
        ResultSummaryView.as_view(),
        name="election-results-summary",
    ),
    path(
        "<str:election_id>/kiosks/",
        KioskRegistrationView.as_view(),
        name="election-kiosk-list-create",
    ),
    path(
        "<str:election_id>/voters/",
        EligibleVoterListCreateView.as_view(),
        name="election-voter-list-create",
    ),
    path(
        "<str:election_id>/voters/<str:user_id>/",
        EligibleVoterDetailView.as_view(),
        name="election-voter-detail",
    ),
    path(
        "<str:election_id>/my-eligibility/",
        MyEligibilityView.as_view(),
        name="election-my-eligibility",
    ),
    path("<str:election_id>/vote/", CastVoteView.as_view(), name="election-cast-vote"),
]
