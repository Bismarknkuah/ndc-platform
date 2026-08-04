from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.messaging.documents import Broadcast, BroadcastAcknowledgement
from apps.messaging.permissions import can_issue_broadcast
from apps.messaging.serializers import (
    BroadcastAcknowledgementSerializer,
    BroadcastSerializer,
)
from apps.messaging.services import notify_many, units_in_subtree, users_in_subtree


def _get_broadcast_or_404(broadcast_id):
    try:
        return Broadcast.objects.get(id=broadcast_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Broadcast not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


def _can_view_broadcast(user, broadcast) -> bool:
    if user.is_superadmin or broadcast.issued_by.id == user.id:
        return True
    if user.organizational_unit is None:
        return False
    return user.organizational_unit in units_in_subtree(broadcast.target_unit)


class BroadcastListCreateView(APIView):
    """
    GET  /api/v1/messaging/broadcasts/?target_unit_id=&kind=
         Broadcasts visible to the caller: everything they issued, plus
         everything targeted at their own unit's subtree membership
         (i.e. anything addressed to their unit or an ancestor of it).

    POST /api/v1/messaging/broadcasts/
         Issue a directive or announcement down the caller's own chain of
         command. Notifies every active member in the target subtree.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: BroadcastSerializer(many=True)}, tags=["messaging"])
    def get(self, request):
        user = request.user
        if user.is_superadmin:
            qs = Broadcast.objects.all()
        else:
            # Visible to caller: issued by them, or targeted at an ancestor
            # of (or exactly) their own unit.
            ancestor_ids = (
                [
                    a.id
                    for a in (
                        [user.organizational_unit]
                        + user.organizational_unit.get_ancestors()
                    )
                ]
                if user.organizational_unit
                else []
            )
            qs = Broadcast.objects(
                __raw__={
                    "$or": [
                        {"issued_by": user.id},
                        {"target_unit": {"$in": ancestor_ids}},
                    ]
                }
            )

        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)

        target_unit_id = request.query_params.get("target_unit_id")
        if target_unit_id:
            qs = qs.filter(target_unit=target_unit_id)

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            BroadcastSerializer(page, many=True).data
        )

    @extend_schema(
        request=BroadcastSerializer,
        responses={201: BroadcastSerializer},
        tags=["messaging"],
    )
    def post(self, request):
        serializer = BroadcastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["target_unit_id"]

        if not can_issue_broadcast(request.user, target_unit):
            raise APIError(
                "You do not have authority to broadcast to this unit's chain of command.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        broadcast = Broadcast.objects.create(
            title=serializer.validated_data["title"],
            body=serializer.validated_data["body"],
            kind=serializer.validated_data["kind"],
            priority=serializer.validated_data.get("priority", "NORMAL"),
            issued_by=request.user,
            target_unit=target_unit,
            requires_acknowledgement=serializer.validated_data.get(
                "requires_acknowledgement", False
            ),
        )

        recipients = users_in_subtree(target_unit, exclude_user=request.user)
        notify_many(
            recipients,
            "BROADCAST",
            title=f"{'Directive' if broadcast.kind == 'DIRECTIVE' else 'Announcement'}: {broadcast.title}",
            body=broadcast.body[:200],
            target=broadcast,
        )

        log_action(
            request.user,
            "messaging.broadcast.issue",
            request=request,
            target=broadcast,
            description=f"{broadcast.kind} to {target_unit.name}: {broadcast.title}",
            metadata={"recipient_count": len(recipients)},
        )
        return Response(
            BroadcastSerializer(broadcast).data, status=status.HTTP_201_CREATED
        )


class BroadcastAcknowledgeView(APIView):
    """POST /api/v1/messaging/broadcasts/<id>/acknowledge/ - the caller acknowledges receipt."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={201: BroadcastAcknowledgementSerializer},
        tags=["messaging"],
    )
    def post(self, request, broadcast_id):
        broadcast = _get_broadcast_or_404(broadcast_id)
        if not _can_view_broadcast(request.user, broadcast):
            raise APIError(
                "This broadcast was not addressed to you.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        ack = BroadcastAcknowledgement.objects(
            broadcast=broadcast, user=request.user
        ).first()
        if ack is None:
            ack = BroadcastAcknowledgement.objects.create(
                broadcast=broadcast, user=request.user
            )
            log_action(
                request.user,
                "messaging.broadcast.acknowledge",
                request=request,
                target=broadcast,
            )
        return Response(
            BroadcastAcknowledgementSerializer(ack).data, status=status.HTTP_201_CREATED
        )


class BroadcastAcknowledgementsListView(APIView):
    """GET /api/v1/messaging/broadcasts/<id>/acknowledgements/ - who has acknowledged (issuer/authority only)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: BroadcastAcknowledgementSerializer(many=True)},
        tags=["messaging"],
    )
    def get(self, request, broadcast_id):
        broadcast = _get_broadcast_or_404(broadcast_id)
        if not (
            request.user.is_superadmin or broadcast.issued_by.id == request.user.id
        ):
            raise APIError(
                "Only the issuer can view acknowledgement status.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        acks = BroadcastAcknowledgement.objects(broadcast=broadcast).order_by(
            "-acknowledged_at"
        )
        recipients = users_in_subtree(broadcast.target_unit)
        return Response(
            {
                "total_recipients": len(recipients),
                "acknowledged_count": acks.count(),
                "acknowledgements": BroadcastAcknowledgementSerializer(
                    acks, many=True
                ).data,
            }
        )
