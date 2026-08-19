from django.urls import path

from apps.membership.views import (
    MyMembershipCardView,
    ReissueMembershipCardView,
    VerifyMembershipCardView,
)

urlpatterns = [
    path("card/", MyMembershipCardView.as_view(), name="my-membership-card"),
    path(
        "card/reissue/",
        ReissueMembershipCardView.as_view(),
        name="reissue-membership-card",
    ),
    path("verify/", VerifyMembershipCardView.as_view(), name="verify-membership-card"),
]
