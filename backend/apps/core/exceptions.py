import logging

from mongoengine.errors import DoesNotExist, NotUniqueError, ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("ndc")


class APIError(Exception):
    """Raise for domain-level errors that should surface as clean API responses."""

    def __init__(self, message, code="error", http_status=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.code = code
        self.http_status = http_status
        super().__init__(message)


def api_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler so every error, including
    MongoEngine-specific errors and our own APIError, returns a
    consistent JSON envelope:

        {"error": {"code": "...", "message": "...", "details": {...}}}
    """
    if isinstance(exc, APIError):
        return Response(
            {"error": {"code": exc.code, "message": exc.message}},
            status=exc.http_status,
        )

    if isinstance(exc, DoesNotExist):
        return Response(
            {
                "error": {
                    "code": "not_found",
                    "message": "The requested resource was not found.",
                }
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, NotUniqueError):
        return Response(
            {
                "error": {
                    "code": "conflict",
                    "message": "A resource with these unique fields already exists.",
                }
            },
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, ValidationError):
        return Response(
            {
                "error": {
                    "code": "validation_error",
                    "message": str(exc),
                    "details": getattr(exc, "errors", {}),
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": {
                "code": "error",
                "message": (
                    response.data if isinstance(response.data, str) else response.data
                ),
            }
        }
        return response

    logger.exception("Unhandled exception in %s", context.get("view"))
    return Response(
        {
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred.",
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
