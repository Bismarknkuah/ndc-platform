from django.urls import path

from apps.dues.views import (
    DuesPaymentHistoryView,
    DuesPaymentWebhookView,
    InitializeDuesPaymentView,
    VerifyDuesPaymentView,
)

urlpatterns = [
    path("initialize/", InitializeDuesPaymentView.as_view(), name="dues-initialize"),
    path(
        "verify/<str:reference>/", VerifyDuesPaymentView.as_view(), name="dues-verify"
    ),
    path("webhook/", DuesPaymentWebhookView.as_view(), name="dues-webhook"),
    path("history/", DuesPaymentHistoryView.as_view(), name="dues-history"),
]
