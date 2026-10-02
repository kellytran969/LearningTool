"""Pagination for the API."""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Page-number pagination: 12 per page, client-adjustable up to 50."""

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50
