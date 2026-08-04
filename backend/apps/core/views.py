import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsNationalOfficer
from apps.core.audit import AuditLog
from apps.core.pagination import paginate_queryset

logger = logging.getLogger("ndc")


class HealthCheckView(APIView):
    """
    GET /api/v1/health/ - unauthenticated liveness/readiness probe that
    actually verifies the MongoDB connection, not just that the Django
    process is running. Point Kubernetes probes / the Docker HEALTHCHECK
    here instead of an arbitrary authenticated endpoint.
    """

    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["health"])
    def get(self, request):
        import mongoengine

        try:
            mongoengine.connection.get_db().command("ping")
            mongo_ok = True
        except Exception:
            # Previously a bare `except Exception: mongo_ok = False` with no
            # logging at all - meant a failing healthcheck gave zero signal
            # in the deploy logs about *why* (Atlas auth failure vs. network
            # access vs. TLS vs. wrong URI). Logged here, not returned in the
            # response body, since this is an unauthenticated public
            # endpoint and a raw exception could echo connection details.
            logger.exception("Health check: MongoDB ping failed")
            mongo_ok = False

        healthy = mongo_ok
        return Response(
            {"status": "ok" if healthy else "degraded", "mongodb": mongo_ok},
            status=200 if healthy else 503,
        )


class AuditLogListView(APIView):
    """
    GET /api/v1/audit/logs/
    National-level oversight roles can view the full, unified audit trail.
    Supports filtering by ?action=&actor_id=&target_type=
    """

    permission_classes = [IsAuthenticated, IsNationalOfficer]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["audit"])
    def get(self, request):
        qs = AuditLog.objects.all().order_by("-created_at")

        action = request.query_params.get("action")
        if action:
            qs = qs.filter(action__istartswith=action)

        actor_id = request.query_params.get("actor_id")
        if actor_id:
            qs = qs.filter(actor_id=actor_id)

        target_type = request.query_params.get("target_type")
        if target_type:
            qs = qs.filter(target_type=target_type)

        paginator, page = paginate_queryset(qs, request, self)
        data = [
            {
                "id": str(log.id),
                "actor_email": log.actor_email,
                "actor_role": log.actor_role,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "description": log.description,
                "metadata": log.metadata,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in page
        ]
        return paginator.get_paginated_response(data)
