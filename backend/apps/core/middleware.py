import uuid


class AuditRequestMiddleware:
    """
    Attaches a request_id and resolved client IP to every request so that
    views/services can pass rich context into AuditLog entries without
    re-deriving it. Does not itself write to the audit collection - that
    stays an explicit, intentional call at the point of a meaningful
    business action (see apps.core.audit.log_action).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        request.client_ip = self._get_client_ip(request)
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response

    @staticmethod
    def _get_client_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
