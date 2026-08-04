from django.urls import path

from apps.hierarchy.views import (
    OrganizationalUnitAncestorsView,
    OrganizationalUnitDescendantsView,
    OrganizationalUnitDetailView,
    OrganizationalUnitListCreateView,
)

urlpatterns = [
    path("units/", OrganizationalUnitListCreateView.as_view(), name="unit-list-create"),
    path(
        "units/<str:unit_id>/",
        OrganizationalUnitDetailView.as_view(),
        name="unit-detail",
    ),
    path(
        "units/<str:unit_id>/descendants/",
        OrganizationalUnitDescendantsView.as_view(),
        name="unit-descendants",
    ),
    path(
        "units/<str:unit_id>/ancestors/",
        OrganizationalUnitAncestorsView.as_view(),
        name="unit-ancestors",
    ),
]
