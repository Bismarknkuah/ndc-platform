from django.urls import path

from apps.documents.views import PartyDocumentDetailView, PartyDocumentListCreateView

urlpatterns = [
    path("", PartyDocumentListCreateView.as_view(), name="document-list-create"),
    path(
        "<str:document_id>/", PartyDocumentDetailView.as_view(), name="document-detail"
    ),
]
