from django.urls import path

from apps.kiosk.views import KioskCastVoteView, KioskVerifyView, SetKioskPinView

urlpatterns = [
    path("verify/", KioskVerifyView.as_view(), name="kiosk-verify"),
    path("vote/", KioskCastVoteView.as_view(), name="kiosk-cast-vote"),
    path("my-pin/", SetKioskPinView.as_view(), name="kiosk-set-pin"),
]
