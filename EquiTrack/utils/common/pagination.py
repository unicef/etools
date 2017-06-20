from rest_framework.pagination import PageNumberPagination


class DisableablePaginationMixin(object):
    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                if request.query_params[self.page_size_query_param] == 'all':
                    return None
            except KeyError:
                pass
        return super(DisableablePaginationMixin, self).get_page_size(request)


class DynamicPageNumberPagination(DisableablePaginationMixin, PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000
