from django.urls import path

from apps.departments.views import (
    DepartmentAssignmentDetailView,
    DepartmentAssignmentListCreateView,
    DepartmentListCreateView,
    DepartmentTeamDashboardView,
    MyDepartmentAssignmentsView,
    TaskAssignmentDetailView,
    TaskAssignmentListCreateView,
)

urlpatterns = [
    path("", DepartmentListCreateView.as_view(), name="department-list-create"),
    path(
        "assignments/",
        DepartmentAssignmentListCreateView.as_view(),
        name="department-assignment-list-create",
    ),
    path(
        "assignments/<str:assignment_id>/",
        DepartmentAssignmentDetailView.as_view(),
        name="department-assignment-detail",
    ),
    path(
        "my-assignments/",
        MyDepartmentAssignmentsView.as_view(),
        name="my-department-assignments",
    ),
    path(
        "dashboard/",
        DepartmentTeamDashboardView.as_view(),
        name="department-team-dashboard",
    ),
    path(
        "tasks/",
        TaskAssignmentListCreateView.as_view(),
        name="department-task-list-create",
    ),
    path(
        "tasks/<str:task_id>/",
        TaskAssignmentDetailView.as_view(),
        name="department-task-detail",
    ),
]
