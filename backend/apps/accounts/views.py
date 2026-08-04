from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import (
    TokenError,
    issue_token_pair,
    refresh_access_token,
    revoke_token,
)
from apps.accounts.documents import Role, User
from apps.accounts.permissions import (
    HasRolePermission,
    can_manage_members_at,
    can_manage_roles,
)
from apps.accounts.serializers import (
    AdminCreateMemberSerializer,
    AssignRoleSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    MemberAdminUpdateSerializer,
    MemberTransferSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    RoleSerializer,
    RoleWriteSerializer,
    UserSerializer,
    generate_membership_id,
    get_or_create_ordinary_role,
)
from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.hierarchy.documents import OrganizationalUnit


class RegisterView(APIView):
    """POST /api/v1/auth/register/ - self-service Ordinary Member signup."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        request=RegisterSerializer, responses={201: UserSerializer}, tags=["auth"]
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_action(
            user,
            "user.register",
            request=request,
            target=user,
            description="Self-service registration",
        )
        tokens = issue_token_pair(user)
        return Response(
            {"user": UserSerializer(user).data, "tokens": tokens},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/v1/auth/login/"""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        request=LoginSerializer, responses={200: UserSerializer}, tags=["auth"]
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = User.objects(email=email).first()
        if user is None or not user.check_password(password):
            raise APIError(
                "Invalid email or password.",
                code="invalid_credentials",
                http_status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            raise APIError(
                "This account has been deactivated.",
                code="account_inactive",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        import datetime

        user.last_login = datetime.datetime.utcnow()
        user.save()

        log_action(user, "user.login", request=request, target=user)
        tokens = issue_token_pair(user)
        return Response({"user": UserSerializer(user).data, "tokens": tokens})


class RefreshTokenView(APIView):
    """POST /api/v1/auth/refresh/"""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        request=RefreshTokenSerializer,
        responses={200: OpenApiResponse(description="New access/refresh token pair")},
        tags=["auth"],
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tokens = refresh_access_token(serializer.validated_data["refresh"])
        except TokenError as exc:
            raise APIError(
                str(exc), code="invalid_token", http_status=status.HTTP_401_UNAUTHORIZED
            ) from exc
        return Response(tokens)


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ - revokes the supplied refresh token."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=RefreshTokenSerializer, responses={204: None}, tags=["auth"])
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            revoke_token(serializer.validated_data["refresh"], expected_type="refresh")
        except TokenError as exc:
            raise APIError(
                str(exc), code="invalid_token", http_status=status.HTTP_401_UNAUTHORIZED
            ) from exc
        log_action(request.user, "user.logout", request=request, target=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET/PATCH /api/v1/auth/me/ - the authenticated user's own profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer}, tags=["auth"])
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        request=UserSerializer, responses={200: UserSerializer}, tags=["auth"]
    )
    def patch(self, request):
        user = request.user
        editable_fields = (
            "first_name",
            "last_name",
            "gender",
            "residential_address",
            "occupation",
            "marital_status",
            "emergency_contact_name",
            "emergency_contact_phone",
        )
        for field in editable_fields:
            if field in request.data:
                setattr(user, field, request.data[field])

        if "photo_base64" in request.data:
            photo_base64 = request.data["photo_base64"]
            if photo_base64:
                # ~2MB cap after base64 expansion - a profile photo has
                # no reason to be as large as a document/media upload,
                # and this keeps the user document itself lightweight
                # (it's fetched on every request via authentication).
                max_encoded_length = 2_800_000
                if len(photo_base64) > max_encoded_length:
                    raise APIError(
                        "Photo is too large (max ~2MB).", code="invalid_input"
                    )
                user.photo_base64 = photo_base64
                user.photo_content_type = request.data.get(
                    "photo_content_type", "image/jpeg"
                )
            else:
                # Explicit empty string/null clears the photo.
                user.photo_base64 = None
                user.photo_content_type = None

        user.save()
        log_action(user, "user.update_profile", request=request, target=user)
        return Response(UserSerializer(user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer, responses={204: None}, tags=["auth"]
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            raise APIError("Old password is incorrect.", code="invalid_credentials")
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        log_action(user, "user.change_password", request=request, target=user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleListCreateView(APIView):
    """
    GET  /api/v1/auth/roles/?scope=&is_active=
         Available party positions. Any authenticated member can browse
         positions (needed for things like self-registration showing
         available roles); only holders of "hierarchy.manage_roles" can
         create new ones.

    POST /api/v1/auth/roles/
         Position Management Module: create a new position (e.g. a new
         Deputy role, or a position for a wing/committee not yet
         modeled) - name, code, scope, permissions, optional reports_to
         and dashboard_config. No deployment required.
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    @extend_schema(responses={200: RoleSerializer(many=True)}, tags=["auth"])
    def get(self, request):
        scope = request.query_params.get("scope")
        qs = Role.objects(is_active=True)
        if scope:
            qs = qs.filter(scope=scope)
        if request.query_params.get("is_active") == "false":
            qs = Role.objects(is_active=False)
        return Response(RoleSerializer(qs, many=True).data)

    @extend_schema(
        request=RoleWriteSerializer, responses={201: RoleSerializer}, tags=["auth"]
    )
    def post(self, request):
        if not can_manage_roles(request.user):
            raise APIError(
                "Only National-level holders of hierarchy.manage_roles can create positions.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RoleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for required in ("name", "code", "scope"):
            if required not in serializer.validated_data:
                raise APIError(
                    f"'{required}' is required to create a position.",
                    code="invalid_input",
                )

        role = Role.objects.create(
            name=serializer.validated_data["name"],
            code=serializer.validated_data["code"],
            scope=serializer.validated_data["scope"],
            is_executive=serializer.validated_data.get("is_executive", True),
            permissions=serializer.validated_data.get("permissions", []),
            reports_to=serializer.validated_data.get("reports_to_id"),
            dashboard_config=serializer.validated_data.get("dashboard_config", {}),
        )
        log_action(
            request.user,
            "accounts.role.create",
            request=request,
            target=role,
            description=role.name,
        )
        return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)


class RoleDetailView(APIView):
    """
    GET    /api/v1/auth/roles/<id>/
    PATCH  /api/v1/auth/roles/<id>/  - rename, redefine permissions/
           reporting line/dashboard config (hierarchy.manage_roles only)
    DELETE /api/v1/auth/roles/<id>/  - retire a position (soft-delete;
           blocked if any active member currently holds it - reassign
           them first)
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def _get_or_404(self, role_id):
        try:
            return Role.objects.get(id=role_id, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Position not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

    @extend_schema(responses={200: RoleSerializer}, tags=["auth"])
    def get(self, request, role_id):
        return Response(RoleSerializer(self._get_or_404(role_id)).data)

    @extend_schema(
        request=RoleWriteSerializer, responses={200: RoleSerializer}, tags=["auth"]
    )
    def patch(self, request, role_id):
        if not can_manage_roles(request.user):
            raise APIError(
                "Only National-level holders of hierarchy.manage_roles can edit positions.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        role = self._get_or_404(role_id)
        serializer = RoleWriteSerializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        for field in (
            "name",
            "code",
            "scope",
            "is_executive",
            "permissions",
            "dashboard_config",
        ):
            if field in serializer.validated_data:
                setattr(role, field, serializer.validated_data[field])
        if "reports_to_id" in serializer.validated_data:
            role.reports_to = serializer.validated_data["reports_to_id"]

        role.save()
        log_action(
            request.user,
            "accounts.role.update",
            request=request,
            target=role,
            description=role.name,
        )
        return Response(RoleSerializer(role).data)

    @extend_schema(responses={204: None}, tags=["auth"])
    def delete(self, request, role_id):
        if not can_manage_roles(request.user):
            raise APIError(
                "Only National-level holders of hierarchy.manage_roles can retire positions.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        role = self._get_or_404(role_id)
        if User.objects(role=role, is_active=True).first():
            raise APIError(
                "This position is currently held by at least one active member - reassign them first.",
                code="conflict",
                http_status=status.HTTP_409_CONFLICT,
            )
        role.is_active = False
        role.save()
        log_action(
            request.user,
            "accounts.role.retire",
            request=request,
            target=role,
            description=role.name,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssignRoleView(APIView):
    """
    POST /api/v1/auth/assign-role/
    Privileged action for appointing/changing a member's executive role.
    Requires the "hierarchy.manage_roles" permission on the acting user's
    role, and the acting user's organizational unit must be the target
    role's unit or an ancestor of it (a Regional officer cannot appoint a
    National officer, but a National officer can appoint at any level).
    """

    permission_classes = [
        IsAuthenticated,
        HasRolePermission.requiring("hierarchy.manage_roles"),
    ]

    @extend_schema(
        request=AssignRoleSerializer, responses={200: UserSerializer}, tags=["auth"]
    )
    def post(self, request):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user = serializer.validated_data["user_id"]
        new_role = serializer.validated_data["role_id"]

        acting_user = request.user
        if not acting_user.is_superadmin:
            acting_unit = acting_user.organizational_unit
            target_unit = target_user.organizational_unit
            if not (
                acting_unit
                and target_unit
                and acting_unit.is_same_or_ancestor_of(target_unit)
            ):
                raise APIError(
                    "You do not have authority over this member's organizational unit.",
                    code="forbidden",
                    http_status=status.HTTP_403_FORBIDDEN,
                )

        previous_role = target_user.role.code if target_user.role else None
        target_user.role = new_role
        target_user.save()

        log_action(
            acting_user,
            "user.assign_role",
            request=request,
            target=target_user,
            description=f"Role changed from {previous_role} to {new_role.code}",
            metadata={"previous_role": previous_role, "new_role": new_role.code},
        )
        return Response(UserSerializer(target_user).data)


def _generate_temp_password() -> str:
    import secrets

    return secrets.token_urlsafe(12)


def _create_member_for_executive(acting_user, data: dict, request=None):
    """
    Shared logic for AdminCreateMemberView and AdminBulkCreateMembersView.
    Validates authority, creates the User (+ optional DepartmentAssignment),
    and returns (user, temp_password). Raises APIError on any failure so
    both the single and bulk endpoints get identical, consistent errors.
    """
    serializer = AdminCreateMemberSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    target_unit = serializer.validated_data["organizational_unit_id"]

    if not can_manage_members_at(acting_user, target_unit):
        raise APIError(
            "You do not have authority to add members at this organizational unit.",
            code="forbidden",
            http_status=status.HTTP_403_FORBIDDEN,
        )

    department = serializer.validated_data.get("department_id")
    department_position = serializer.validated_data.get("department_position")
    if department:
        # Local import: apps.departments imports apps.accounts.documents,
        # so importing at module level here would create a circular import.
        from apps.departments.documents import Department, DepartmentAssignment
        from apps.departments.permissions import has_department_authority

        try:
            department_obj = Department.objects.get(id=department, is_active=True)
        except Exception as exc:
            raise APIError(
                "Department not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc
        if not has_department_authority(acting_user, department_obj, target_unit):
            raise APIError(
                "You do not have department authority at this organizational unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
    else:
        department_obj = None

    role = serializer.validated_data.get("role_id") or get_or_create_ordinary_role()

    user = User(
        email=serializer.validated_data["email"],
        phone_number=serializer.validated_data["phone_number"],
        first_name=serializer.validated_data["first_name"],
        last_name=serializer.validated_data["last_name"],
        gender=serializer.validated_data.get("gender"),
        date_of_birth=serializer.validated_data.get("date_of_birth"),
        national_id_number=serializer.validated_data["national_id_number"],
        residential_address=serializer.validated_data["residential_address"],
        emergency_contact_name=serializer.validated_data["emergency_contact_name"],
        emergency_contact_phone=serializer.validated_data["emergency_contact_phone"],
        occupation=serializer.validated_data.get("occupation", ""),
        marital_status=serializer.validated_data.get("marital_status"),
        organizational_unit=target_unit,
        role=role,
        membership_id=generate_membership_id(target_unit),
        must_change_password=True,
    )
    if serializer.validated_data.get("voter_id_number"):
        user.voter_id_number = serializer.validated_data["voter_id_number"]
    temp_password = _generate_temp_password()
    user.set_password(temp_password)
    user.save()

    if department_obj:
        DepartmentAssignment.objects.create(
            user=user,
            department=department_obj,
            organizational_unit=target_unit,
            position=department_position,
            appointed_by=acting_user,
        )

    log_action(
        acting_user,
        "user.admin_create",
        request=request,
        target=user,
        description=f"Provisioned {user.full_name} ({role.code}) at {target_unit.name}",
        metadata={"department": department_obj.code if department_obj else None},
    )
    return user, temp_password


class AdminCreateMemberView(APIView):
    """
    POST /api/v1/auth/members/
    An executive with hierarchy authority over `organizational_unit_id`
    (e.g. a Constituency/"district" chairman provisioning a Branch
    Chairman) creates a member account directly, optionally placing them
    into a department in the same call. Returns a one-time temporary
    password; the account is flagged must_change_password.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=AdminCreateMemberSerializer,
        responses={
            201: OpenApiResponse(
                description="Created member + one-time temporary password"
            )
        },
        tags=["auth"],
    )
    def post(self, request):
        user, temp_password = _create_member_for_executive(
            request.user, request.data, request=request
        )
        return Response(
            {"user": UserSerializer(user).data, "temporary_password": temp_password},
            status=status.HTTP_201_CREATED,
        )


class AdminBulkCreateMembersView(APIView):
    """
    POST /api/v1/auth/members/bulk/
    Provision many members in one call - e.g. a Constituency chairman
    entering the Branch Chairman and Branch Secretary for every branch in
    their constituency at once. Body: {"members": [ {...}, {...} ]}. Each
    entry is validated and authorized independently; one bad entry does
    not block the rest. Response lists successes and per-index errors.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={207: OpenApiResponse(description="Per-item created/errors report")},
        tags=["auth"],
    )
    def post(self, request):
        entries = request.data.get("members")
        if not isinstance(entries, list) or not entries:
            raise APIError(
                "Expected a non-empty 'members' list.",
                code="invalid_input",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        errors = []
        for index, entry in enumerate(entries):
            try:
                user, temp_password = _create_member_for_executive(
                    request.user, entry, request=request
                )
                created.append(
                    {
                        "index": index,
                        "user": UserSerializer(user).data,
                        "temporary_password": temp_password,
                    }
                )
            except APIError as exc:
                errors.append(
                    {"index": index, "code": exc.code, "message": exc.message}
                )
            except Exception as exc:  # serializer ValidationError, etc.
                detail = exc.detail if hasattr(exc, "detail") else str(exc)
                errors.append(
                    {"index": index, "code": "validation_error", "message": detail}
                )

        return Response(
            {"created": created, "errors": errors}, status=status.HTTP_207_MULTI_STATUS
        )


class MemberListView(APIView):
    """
    GET /api/v1/auth/members/list/?search=&organizational_unit_id=&role_id=&is_active=

    Search/list members. If organizational_unit_id is supplied, requires
    hierarchy.manage/membership.register authority over that unit
    (ancestor-scoped, same rule as provisioning members there). If
    omitted, defaults to the caller's own unit subtree, and requires the
    caller to hold that same authority somewhere - ordinary members
    cannot browse the full membership directory (it contains national ID
    numbers and other sensitive data).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer(many=True)}, tags=["auth"])
    def get(self, request):
        organizational_unit_id = request.query_params.get("organizational_unit_id")
        if organizational_unit_id:
            try:
                unit = OrganizationalUnit.objects.get(
                    id=organizational_unit_id, is_active=True
                )
            except (DoesNotExist, MongoValidationError) as exc:
                raise APIError(
                    "Organizational unit not found.",
                    code="not_found",
                    http_status=status.HTTP_404_NOT_FOUND,
                ) from exc
        else:
            unit = request.user.organizational_unit
            if unit is None:
                raise APIError(
                    "You are not attached to an organizational unit.",
                    code="invalid_state",
                )

        if not can_manage_members_at(request.user, unit):
            raise APIError(
                "You do not have authority to browse members in this jurisdiction.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        from apps.messaging.services import units_in_subtree

        unit_ids = [u.id for u in units_in_subtree(unit)]
        qs = User.objects(organizational_unit__in=unit_ids)

        is_active = request.query_params.get("is_active")
        if is_active == "true":
            qs = qs.filter(is_active=True)
        elif is_active == "false":
            qs = qs.filter(is_active=False)

        role_id = request.query_params.get("role_id")
        if role_id:
            qs = qs.filter(role=role_id)

        search = request.query_params.get("search")
        if search:
            import re

            pattern = re.escape(search)
            qs = qs.filter(
                __raw__={
                    "$or": [
                        {"first_name": {"$regex": pattern, "$options": "i"}},
                        {"last_name": {"$regex": pattern, "$options": "i"}},
                        {"email": {"$regex": pattern, "$options": "i"}},
                        {"membership_id": {"$regex": pattern, "$options": "i"}},
                    ]
                }
            )

        paginator, page = paginate_queryset(
            qs.order_by("last_name", "first_name"), request, self
        )
        return paginator.get_paginated_response(
            UserSerializer(page, many=True, context={"list_view": True}).data
        )


class MemberDetailView(APIView):
    """
    GET   /api/v1/auth/members/<id>/        - view a member's full profile
    PATCH /api/v1/auth/members/<id>/        - suspend/reactivate
          (is_active) or correct basic profile data. Requires authority
          over the member's own organizational unit.
    """

    permission_classes = [IsAuthenticated]

    def _get_or_404(self, member_id):
        try:
            return User.objects.get(id=member_id)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Member not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

    @extend_schema(responses={200: UserSerializer}, tags=["auth"])
    def get(self, request, member_id):
        member = self._get_or_404(member_id)
        if member.id != request.user.id and not can_manage_members_at(
            request.user, member.organizational_unit
        ):
            raise APIError(
                "You do not have authority to view this member.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return Response(UserSerializer(member).data)

    @extend_schema(
        request=MemberAdminUpdateSerializer,
        responses={200: UserSerializer},
        tags=["auth"],
    )
    def patch(self, request, member_id):
        member = self._get_or_404(member_id)
        if not can_manage_members_at(request.user, member.organizational_unit):
            raise APIError(
                "You do not have authority to manage this member.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MemberAdminUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        previous_active = member.is_active
        for field in (
            "first_name",
            "last_name",
            "national_id_number",
            "voter_id_number",
        ):
            if field in serializer.validated_data:
                setattr(member, field, serializer.validated_data[field])
        if "is_active" in serializer.validated_data:
            member.is_active = serializer.validated_data["is_active"]

        member.save()

        if (
            "is_active" in serializer.validated_data
            and previous_active != member.is_active
        ):
            action = (
                "accounts.member.activate"
                if member.is_active
                else "accounts.member.suspend"
            )
            log_action(
                request.user,
                action,
                request=request,
                target=member,
                description=serializer.validated_data.get("deactivation_reason", ""),
            )
        else:
            log_action(
                request.user, "accounts.member.update", request=request, target=member
            )

        return Response(UserSerializer(member).data)


class MemberTransferView(APIView):
    """
    POST /api/v1/auth/members/<id>/transfer/  {"target_organizational_unit_id": "..."}

    Moves a member to a different unit (e.g. a Branch transfer). Requires
    authority over BOTH the member's current unit and the destination
    unit - prevents an officer moving a member out of a jurisdiction they
    don't control, or into one they don't control either.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MemberTransferSerializer, responses={200: UserSerializer}, tags=["auth"]
    )
    def post(self, request, member_id):
        try:
            member = User.objects.get(id=member_id)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Member not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

        serializer = MemberTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["target_organizational_unit_id"]

        if not can_manage_members_at(request.user, member.organizational_unit):
            raise APIError(
                "You do not have authority over this member's current unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if not can_manage_members_at(request.user, target_unit):
            raise APIError(
                "You do not have authority over the destination unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        previous_unit = member.organizational_unit
        member.organizational_unit = target_unit
        member.save()

        log_action(
            request.user,
            "accounts.member.transfer",
            request=request,
            target=member,
            description=f"{previous_unit.name} -> {target_unit.name}",
            metadata={"reason": serializer.validated_data.get("reason", "")},
        )
        return Response(UserSerializer(member).data)
