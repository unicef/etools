from django.core.exceptions import ValidationError
from django.db import connection
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.cache import cache_control, cache_page

from rest_framework import permissions
from rest_framework.request import Request
from unicef_locations import views
from unicef_locations.cache import etag_cached, get_cache_version

from etools.applications.locations.models import Location
from etools.libraries.tenant_support.utils import TenantSuffixedString


def cache_key(request: Request):
    schema_name = connection.schema_name
    url = str(request._request.get_raw_uri())
    return 'locations-etag-%s-%s-%s' % (schema_name, get_cache_version(), slugify(url))


class LocationsLightViewSet(views.LocationsLightViewSet):
    # TODO: check user filter?
    @method_decorator(cache_control(
        max_age=0,  # enable cache yet automatically treat all cached data as stale to request backend every time
        public=True,  # reset cache control header to allow etags work with cache_page
    ))
    @etag_cached('locations')  # etag_cached is idempotent, so it's okay to decorate view with it twice
    @method_decorator(cache_page(60 * 60 * 24, key_prefix=TenantSuffixedString('locations')))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class LocationsViewSet(views.LocationsViewSet):
    # TODO: permissions check
    queryset = Location.objects.all_with_geom()

    # TODO: override and nullify create and update methods
    def get_queryset(self):
        queryset = Location.objects.all_with_geom()
        if "values" in self.request.query_params.keys():
            # Used for ghost data - filter in all(), and return straight away.
            try:
                ids = [int(x) for x in self.request.query_params.get("values").split(",")]
            except ValueError:  # pragma: no-cover
                raise ValidationError("ID values must be integers")
            else:
                queryset = queryset.filter(id__in=ids)
        return queryset

    @method_decorator(cache_control(
        max_age=0,  # enable cache yet automatically treat all cached data as stale to request backend every time
        public=True,  # reset cache control header to allow etags work with cache_page
    ))
    @etag_cached('locations')  # etag_cached is idempotent, so it's okay to decorate view with it twice
    @method_decorator(cache_page(60 * 60 * 24, key_prefix=TenantSuffixedString('locations')))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class LocationQuerySetView(views.LocationQuerySetView):
    pass


class CartoDBTablesView(views.CartoDBTablesView):
    permission_classes = (permissions.IsAdminUser,)
