from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """Standard envelope used across every list endpoint in the platform."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "num_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


def paginate_queryset(queryset, request, view):
    """Helper for paginating plain Python lists / MongoEngine QuerySets in APIViews."""
    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(list(queryset), request, view=view)
    return paginator, page
