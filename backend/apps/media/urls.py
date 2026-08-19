from django.urls import path

from apps.media.views import MediaAssetDetailView, MediaAssetListCreateView

urlpatterns = [
    path("", MediaAssetListCreateView.as_view(), name="media-list-create"),
    path("<str:asset_id>/", MediaAssetDetailView.as_view(), name="media-detail"),
]
