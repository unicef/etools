from rest_framework.pagination import PageNumberPagination


class AppendablePageNumberPagination(PageNumberPagination):
    """
    Don't use pagination by default (if page parameter is not presented), but allow it to be enabled if required
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_page_size(self, request):
        if self.page_query_param in request.query_params:
            return super().get_page_size(request)
        return None
