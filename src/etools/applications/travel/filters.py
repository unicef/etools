from distutils.util import strtobool

from rest_framework.filters import BaseFilterBackend

from etools.applications.travel.models import Trip


class ShowHiddenFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        try:
            show_hidden = strtobool(request.query_params['show_hidden'])
        except (KeyError, ValueError):
            return queryset
        return queryset if show_hidden else queryset.exclude(status=Trip.STATUS_CANCELLED)
