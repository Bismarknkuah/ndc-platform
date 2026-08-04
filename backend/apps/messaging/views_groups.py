from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.documents import User
from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.messaging.documents import DiscussionGroup, GroupMessage
from apps.messaging.serializers import (
    DiscussionGroupSerializer,
    GroupMemberActionSerializer,
    GroupMessageSerializer,
)
from apps.messaging.services import notify_many


def _get_group_or_404(group_id):
    try:
        return DiscussionGroup.objects.get(id=group_id, is_active=True)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Discussion group not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


def _require_membership(user, group):
    if (
        user.is_superadmin
        or group.created_by.id == user.id
        or any(m.id == user.id for m in group.members)
    ):
        return
    raise APIError(
        "You are not a member of this group.",
        code="forbidden",
        http_status=status.HTTP_403_FORBIDDEN,
    )


class DiscussionGroupListCreateView(APIView):
    """
    GET  /api/v1/messaging/groups/ - groups the caller belongs to (or created).
    POST /api/v1/messaging/groups/ - create a new group; creator is auto-added as a member.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: DiscussionGroupSerializer(many=True)}, tags=["messaging"]
    )
    def get(self, request):
        qs = DiscussionGroup.objects(
            is_active=True,
            __raw__={
                "$or": [{"members": request.user.id}, {"created_by": request.user.id}]
            },
        )
        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            DiscussionGroupSerializer(page, many=True).data
        )

    @extend_schema(
        request=DiscussionGroupSerializer,
        responses={201: DiscussionGroupSerializer},
        tags=["messaging"],
    )
    def post(self, request):
        serializer = DiscussionGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        members = serializer.validated_data.get("member_ids", [])
        if request.user not in members:
            members.append(request.user)

        group = DiscussionGroup.objects.create(
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            organizational_unit=serializer.validated_data.get("organizational_unit_id"),
            created_by=request.user,
            members=members,
        )
        log_action(
            request.user,
            "messaging.group.create",
            request=request,
            target=group,
            description=group.name,
        )
        return Response(
            DiscussionGroupSerializer(group).data, status=status.HTTP_201_CREATED
        )


class DiscussionGroupMembersView(APIView):
    """
    POST   /api/v1/messaging/groups/<id>/members/    {"user_id": "..."} - add a member (creator only)
    DELETE /api/v1/messaging/groups/<id>/members/     {"user_id": "..."} - remove a member (creator only)
    """

    permission_classes = [IsAuthenticated]

    def _require_owner(self, request, group):
        if not (request.user.is_superadmin or group.created_by.id == request.user.id):
            raise APIError(
                "Only the group creator can manage membership.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

    @extend_schema(
        request=GroupMemberActionSerializer,
        responses={200: DiscussionGroupSerializer},
        tags=["messaging"],
    )
    def post(self, request, group_id):
        group = _get_group_or_404(group_id)
        self._require_owner(request, group)
        try:
            new_member = User.objects.get(
                id=request.data.get("user_id"), is_active=True
            )
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "User not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

        if not any(m.id == new_member.id for m in group.members):
            group.members.append(new_member)
            group.save()
            log_action(
                request.user,
                "messaging.group.add_member",
                request=request,
                target=group,
                description=new_member.full_name,
            )
        return Response(DiscussionGroupSerializer(group).data)

    @extend_schema(
        request=GroupMemberActionSerializer,
        responses={200: DiscussionGroupSerializer},
        tags=["messaging"],
    )
    def delete(self, request, group_id):
        group = _get_group_or_404(group_id)
        self._require_owner(request, group)
        user_id = request.data.get("user_id")
        group.members = [m for m in group.members if str(m.id) != str(user_id)]
        group.save()
        log_action(
            request.user,
            "messaging.group.remove_member",
            request=request,
            target=group,
            description=str(user_id),
        )
        return Response(DiscussionGroupSerializer(group).data)


class GroupMessageListCreateView(APIView):
    """GET/POST /api/v1/messaging/groups/<id>/messages/ - members only."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: GroupMessageSerializer(many=True)}, tags=["messaging"]
    )
    def get(self, request, group_id):
        group = _get_group_or_404(group_id)
        _require_membership(request.user, group)
        qs = GroupMessage.objects(group=group).order_by("-created_at")
        paginator, page = paginate_queryset(qs, request, self)
        return paginator.get_paginated_response(
            GroupMessageSerializer(page, many=True).data
        )

    @extend_schema(
        request=GroupMessageSerializer,
        responses={201: GroupMessageSerializer},
        tags=["messaging"],
    )
    def post(self, request, group_id):
        group = _get_group_or_404(group_id)
        _require_membership(request.user, group)
        serializer = GroupMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = GroupMessage.objects.create(
            group=group, sender=request.user, body=serializer.validated_data["body"]
        )

        recipients = [m for m in group.members if m.id != request.user.id]
        notify_many(
            recipients,
            "GROUP_MESSAGE",
            title=f"{request.user.full_name} in {group.name}",
            body=message.body[:200],
            target=message,
        )

        return Response(
            GroupMessageSerializer(message).data, status=status.HTTP_201_CREATED
        )
