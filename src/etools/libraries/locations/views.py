from django.db import connection
from django.utils.text import slugify

from rest_framework import permissions
from rest_framework.request import Request
from unicef_locations import views
from unicef_locations.cache import get_cache_version


def cache_key(request: Request):
    schema_name = connection.schema_name
    url = str(request._request.get_raw_uri())
    return 'locations-etag-%s-%s-%s' % (schema_name, get_cache_version(), slugify(url))


class LocationsLightViewSet(views.LocationsLightViewSet):
    pass


class LocationsViewSet(views.LocationsViewSet):
    pass


class LocationQuerySetView(views.LocationQuerySetView):
    pass


class CartoDBTablesView(views.CartoDBTablesView):
    permission_classes = (permissions.IsAdminUser,)
