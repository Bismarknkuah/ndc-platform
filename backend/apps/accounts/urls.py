from django.urls import path

from apps.accounts.views import (
    AdminBulkCreateMembersView,
    AdminCreateMemberView,
    AssignRoleView,
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    MemberDetailView,
    MemberListView,
    MemberTransferView,
    RefreshTokenView,
    RegisterView,
    RoleDetailView,
    RoleListCreateView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("roles/", RoleListCreateView.as_view(), name="auth-roles"),
    path("roles/<str:role_id>/", RoleDetailView.as_view(), name="auth-role-detail"),
    path("assign-role/", AssignRoleView.as_view(), name="auth-assign-role"),
    # Literal sub-paths must precede the generic <member_id> catch-all below.
    path("members/", AdminCreateMemberView.as_view(), name="auth-admin-create-member"),
    path(
        "members/bulk/",
        AdminBulkCreateMembersView.as_view(),
        name="auth-admin-bulk-create-members",
    ),
    path("members/list/", MemberListView.as_view(), name="auth-member-list"),
    path(
        "members/<str:member_id>/",
        MemberDetailView.as_view(),
        name="auth-member-detail",
    ),
    path(
        "members/<str:member_id>/transfer/",
        MemberTransferView.as_view(),
        name="auth-member-transfer",
    ),
]
