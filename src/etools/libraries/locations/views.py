# -*- coding: utf-8 -*-
from django.db import connection
from rest_framework import permissions

from unicef_locations import views


def cache_key():
    schema_name = connection.schema_name
    return '{}-locations-etag'.format(schema_name)


class LocationsLightViewSet(views.LocationsLightViewSet):
    pass


class LocationsViewSet(views.LocationsViewSet):
    pass


class LocationTypesViewSet(views.LocationTypesViewSet):
    permission_classes = (permissions.IsAdminUser,)


class LocationQuerySetView(views.LocationQuerySetView):
    pass


class CartoDBTablesView(views.CartoDBTablesView):
    permission_classes = (permissions.IsAdminUser,)
