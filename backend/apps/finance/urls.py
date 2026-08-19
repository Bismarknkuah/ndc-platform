from django.urls import path

from apps.finance.views import (
    FinanceRecordDetailView,
    FinanceRecordListCreateView,
    FinanceSummaryView,
)

urlpatterns = [
    path("summary/", FinanceSummaryView.as_view(), name="finance-summary"),
    path(
        "records/",
        FinanceRecordListCreateView.as_view(),
        name="finance-record-list-create",
    ),
    path(
        "records/<str:record_id>/",
        FinanceRecordDetailView.as_view(),
        name="finance-record-detail",
    ),
]
