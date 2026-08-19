import datetime

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.departments.documents import Department, DepartmentAssignment, TaskAssignment
from apps.departments.permissions import (
    can_bootstrap_department_head,
    has_department_authority,
    has_general_oversight,
)
from apps.departments.serializers import (
    DepartmentAssignmentSerializer,
    DepartmentSerializer,
    TaskAssignmentSerializer,
)
from apps.hierarchy.documents import OrganizationalUnit


def _get_department_or_404(department_id):
    try:
        return Department.objects.get(id=department_id, is_active=True)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Department not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


def _get_assignment_or_404(assignment_id):
    try:
        return DepartmentAssignment.objects.get(id=assignment_id, is_active=True)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Department assignment not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


def _get_task_or_404(task_id):
    try:
        return TaskAssignment.objects.get(id=task_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Task assignment not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class DepartmentListCreateView(APIView):
    """
    GET  /api/v1/departments/           - list every department (any authenticated user)
    POST /api/v1/departments/           - define a new department (National-level executives only)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: DepartmentSerializer(many=True)}, tags=["departments"]
    )
    def get(self, request):
        qs = Department.objects(is_active=True).order_by("name")
        return Response(DepartmentSerializer(qs, many=True).data)

    @extend_schema(
        request=DepartmentSerializer,
        responses={201: DepartmentSerializer},
        tags=["departments"],
    )
    def post(self, request):
        if not can_bootstrap_department_head(request.user):
            raise APIError(
                "Only National-level executives can define new departments.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department = serializer.save()
        log_action(
            request.user,
            "department.create",
            request=request,
            target=department,
            description=department.name,
        )
        return Response(
            DepartmentSerializer(department).data, status=status.HTTP_201_CREATED
        )


class DepartmentAssignmentListCreateView(APIView):
    """
    GET  /api/v1/departments/assignments/?department_id=&organizational_unit_id=&user_id=
         List department team members / directors. Open to any authenticated
         member (a team roster isn't sensitive), filterable by department,
         unit, or user.

    POST /api/v1/departments/assignments/
         Add someone to a department's chain of command at a unit -
         appoint a director, add a team member, etc. The acting user must
         hold HEAD/DEPUTY_HEAD for that department at the target unit or
         an ancestor of it (or be bootstrapping the very first HEAD as a
         National-level executive).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: DepartmentAssignmentSerializer(many=True)}, tags=["departments"]
    )
    def get(self, request):
        qs = DepartmentAssignment.objects(is_active=True)

        department_id = request.query_params.get("department_id")
        if department_id:
            qs = qs.filter(department=department_id)

        unit_id = request.query_params.get("organizational_unit_id")
        if unit_id:
            qs = qs.filter(organizational_unit=unit_id)

        user_id = request.query_params.get("user_id")
        if user_id:
            qs = qs.filter(user=user_id)

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        data = DepartmentAssignmentSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @extend_schema(
        request=DepartmentAssignmentSerializer,
        responses={201: DepartmentAssignmentSerializer},
        tags=["departments"],
    )
    def post(self, request):
        serializer = DepartmentAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department = serializer.validated_data["department_id"]
        target_unit = serializer.validated_data["organizational_unit_id"]
        position = serializer.validated_data["position"]

        authorized = has_department_authority(request.user, department, target_unit)
        if not authorized and position == "HEAD":
            # Allow a National-level executive to make the very first
            # appointment in a department that has no HEAD anywhere yet.
            no_head_exists_anywhere = not DepartmentAssignment.objects(
                department=department,
                position__in=["HEAD", "DEPUTY_HEAD"],
                is_active=True,
            ).first()
            authorized = no_head_exists_anywhere and can_bootstrap_department_head(
                request.user
            )

        if not authorized:
            raise APIError(
                "You do not have management authority over this department at this organizational unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        assignment = DepartmentAssignment.objects.create(
            user=serializer.validated_data["user_id"],
            department=department,
            organizational_unit=target_unit,
            position=position,
            appointed_by=request.user,
        )
        log_action(
            request.user,
            "department.assignment.create",
            request=request,
            target=assignment,
            description=(
                f"Appointed {assignment.user.full_name} as {position} "
                f"of {department.name} at {target_unit.name}"
            ),
        )
        return Response(
            DepartmentAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class DepartmentAssignmentDetailView(APIView):
    """DELETE /api/v1/departments/assignments/<id>/ - remove (deactivate) a department assignment."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None}, tags=["departments"])
    def delete(self, request, assignment_id):
        assignment = _get_assignment_or_404(assignment_id)

        if not has_department_authority(
            request.user, assignment.department, assignment.organizational_unit
        ):
            raise APIError(
                "You do not have management authority over this department at this organizational unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        assignment.is_active = False
        assignment.save()
        log_action(
            request.user,
            "department.assignment.remove",
            request=request,
            target=assignment,
            description=(
                f"Removed {assignment.user.full_name} from "
                f"{assignment.department.name} at {assignment.organizational_unit.name}"
            ),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyDepartmentAssignmentsView(APIView):
    """GET /api/v1/departments/my-assignments/ - the authenticated user's own active department roles."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: DepartmentAssignmentSerializer(many=True)}, tags=["departments"]
    )
    def get(self, request):
        qs = DepartmentAssignment.objects(user=request.user, is_active=True)
        return Response(DepartmentAssignmentSerializer(qs, many=True).data)


class TaskAssignmentListCreateView(APIView):
    """
    GET  /api/v1/departments/tasks/?assigned_to_id=&department_id=&status=
         Defaults to the caller's own tasks (assigned_to=me) unless an
         assigned_to_id is supplied and the caller has department
         authority - or general hierarchy oversight of that member's
         unit - to view another member's diary.

    POST /api/v1/departments/tasks/
         Assign a diary task ("go on Joy FM at 6pm on the 10th") to a
         department member. Requires department authority over the
         target member's own department assignment unit.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: TaskAssignmentSerializer(many=True)}, tags=["departments"]
    )
    def get(self, request):
        assigned_to_id = request.query_params.get("assigned_to_id")

        if assigned_to_id and assigned_to_id != str(request.user.id):
            # Viewing someone else's diary requires department authority
            # over at least one of their active department assignments.
            target_assignments = DepartmentAssignment.objects(
                user=assigned_to_id, is_active=True
            )
            allowed = request.user.is_superadmin or any(
                has_department_authority(
                    request.user, a.department, a.organizational_unit
                )
                or has_general_oversight(request.user, a.organizational_unit)
                for a in target_assignments
            )
            if not allowed:
                raise APIError(
                    "You do not have authority to view this member's task diary.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            qs = TaskAssignment.objects(assigned_to=assigned_to_id)
        else:
            qs = TaskAssignment.objects(assigned_to=request.user)

        department_id = request.query_params.get("department_id")
        if department_id:
            qs = qs.filter(department=department_id)

        task_status = request.query_params.get("status")
        if task_status:
            qs = qs.filter(status=task_status)

        paginator, page = paginate_queryset(qs.order_by("-scheduled_at"), request, self)
        data = TaskAssignmentSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @extend_schema(
        request=TaskAssignmentSerializer,
        responses={201: TaskAssignmentSerializer},
        tags=["departments"],
    )
    def post(self, request):
        serializer = TaskAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department = serializer.validated_data["department_id"]
        assigned_to = serializer.validated_data["assigned_to_id"]

        target_membership = DepartmentAssignment.objects(
            user=assigned_to, department=department, is_active=True
        ).first()
        if target_membership is None:
            raise APIError(
                "This member does not hold an active assignment in this department.",
                code="not_a_department_member",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        if not has_department_authority(
            request.user, department, target_membership.organizational_unit
        ):
            raise APIError(
                "You do not have authority to assign tasks to this member.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        serializer.validated_data["assigned_by"] = request.user
        task = serializer.save()
        log_action(
            request.user,
            "department.task.assign",
            request=request,
            target=task,
            description=f"Assigned '{task.title}' to {assigned_to.full_name}",
            metadata={
                "engagement_type": task.engagement_type,
                "platform_name": task.platform_name,
            },
        )
        return Response(
            TaskAssignmentSerializer(task).data, status=status.HTTP_201_CREATED
        )


class TaskAssignmentDetailView(APIView):
    """
    GET   /api/v1/departments/tasks/<id>/
    PATCH /api/v1/departments/tasks/<id>/  - assignee acknowledges/completes;
          assigner (or anyone with authority over the assignee's unit) can
          cancel or edit.
    """

    permission_classes = [IsAuthenticated]

    def _check_view_permission(self, request, task):
        if (
            request.user.is_superadmin
            or task.assigned_to.id == request.user.id
            or task.assigned_by.id == request.user.id
        ):
            return
        membership = DepartmentAssignment.objects(
            user=task.assigned_to, department=task.department, is_active=True
        ).first()
        if membership and has_department_authority(
            request.user, task.department, membership.organizational_unit
        ):
            return
        raise APIError(
            "You do not have access to this task.",
            code="forbidden",
            http_status=status.HTTP_403_FORBIDDEN,
        )

    @extend_schema(responses={200: TaskAssignmentSerializer}, tags=["departments"])
    def get(self, request, task_id):
        task = _get_task_or_404(task_id)
        self._check_view_permission(request, task)
        return Response(TaskAssignmentSerializer(task).data)

    @extend_schema(
        request=TaskAssignmentSerializer,
        responses={200: TaskAssignmentSerializer},
        tags=["departments"],
    )
    def patch(self, request, task_id):
        task = _get_task_or_404(task_id)
        new_status = request.data.get("status")

        is_assignee = task.assigned_to.id == request.user.id
        membership = DepartmentAssignment.objects(
            user=task.assigned_to, department=task.department, is_active=True
        ).first()
        has_authority = request.user.is_superadmin or (
            membership is not None
            and has_department_authority(
                request.user, task.department, membership.organizational_unit
            )
        )

        if new_status:
            if new_status in ("ACKNOWLEDGED", "COMPLETED") and not (
                is_assignee or has_authority
            ):
                raise APIError(
                    "Only the assignee (or a departmental authority) can update this status.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )
            if new_status == "CANCELLED" and not has_authority:
                raise APIError(
                    "Only a departmental authority can cancel a task.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )

            if new_status == "ACKNOWLEDGED":
                task.mark_acknowledged()
            elif new_status == "COMPLETED":
                task.mark_completed()
            elif new_status == "CANCELLED":
                task.status = "CANCELLED"

        if not (is_assignee or has_authority):
            raise APIError(
                "You do not have permission to modify this task.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        for field in (
            "title",
            "description",
            "engagement_type",
            "platform_name",
            "location",
            "scheduled_at",
        ):
            if field in request.data and has_authority:
                setattr(task, field, request.data[field])

        task.save()
        log_action(
            request.user,
            "department.task.update",
            request=request,
            target=task,
            description=f"status={task.status}",
        )
        return Response(TaskAssignmentSerializer(task).data)


class DepartmentTeamDashboardView(APIView):
    """
    GET /api/v1/departments/dashboard/?department_id=&organizational_unit_id=

    Aggregated view for a department's team at a specific unit - e.g. "the
    National Communications team" or "the Ashanti Regional Communications
    team" or "the Kumasi Central district Communications team". Shows the
    roster, each member's task counts, and the team's upcoming diary.
    Visible to anyone with authority over that specific department+unit,
    a member of that specific team looking at their own team's
    dashboard, or anyone with broad hierarchy oversight of the unit
    (National Chairman, Flagbearer, a Regional Chairman over their own
    region) even without a department-specific assignment there - a
    regular department member sees only their own department, but real
    executive oversight authority is not scoped to one department.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["departments"])
    def get(self, request):
        department_id = request.query_params.get("department_id")
        unit_id = request.query_params.get("organizational_unit_id")
        if not department_id or not unit_id:
            raise APIError(
                "department_id and organizational_unit_id are both required.",
                code="invalid_input",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        department = _get_department_or_404(department_id)
        try:
            unit = OrganizationalUnit.objects.get(id=unit_id, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Organizational unit not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

        is_team_member = (
            DepartmentAssignment.objects(
                user=request.user,
                department=department,
                organizational_unit=unit,
                is_active=True,
            ).first()
            is not None
        )
        if not (
            request.user.is_superadmin
            or has_department_authority(request.user, department, unit)
            or has_general_oversight(request.user, unit)
            or is_team_member
        ):
            raise APIError(
                "You do not have access to this team's dashboard.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        team_assignments = list(
            DepartmentAssignment.objects(
                department=department, organizational_unit=unit, is_active=True
            )
        )
        team_user_ids = [a.user.id for a in team_assignments]

        now = datetime.datetime.utcnow()
        week_ago = now - datetime.timedelta(days=7)

        roster = []
        for assignment in team_assignments:
            pending = TaskAssignment.objects(
                department=department,
                assigned_to=assignment.user,
                status__in=["PENDING", "ACKNOWLEDGED"],
            ).count()
            completed_this_week = TaskAssignment.objects(
                department=department,
                assigned_to=assignment.user,
                status="COMPLETED",
                completed_at__gte=week_ago,
            ).count()
            roster.append(
                {
                    "user": {
                        "id": str(assignment.user.id),
                        "full_name": assignment.user.full_name,
                        "email": assignment.user.email,
                    },
                    "position": assignment.position,
                    "pending_tasks": pending,
                    "completed_tasks_this_week": completed_this_week,
                }
            )

        upcoming_tasks = TaskAssignment.objects(
            department=department,
            assigned_to__in=team_user_ids,
            status__in=["PENDING", "ACKNOWLEDGED"],
            scheduled_at__gte=now,
        ).order_by("scheduled_at")[:10]

        return Response(
            {
                "department": {
                    "id": str(department.id),
                    "name": department.name,
                    "code": department.code,
                },
                "organizational_unit": {
                    "id": str(unit.id),
                    "name": unit.name,
                    "unit_type": unit.unit_type,
                },
                "team_size": len(team_assignments),
                "roster": roster,
                "upcoming_tasks": TaskAssignmentSerializer(
                    upcoming_tasks, many=True
                ).data,
                "total_pending_tasks": sum(r["pending_tasks"] for r in roster),
            }
        )
