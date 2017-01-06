__author__ = 'unicef-leb-inn'
import uuid

from dal import autocomplete
from django.db import connection
from django.core.cache import cache
from django.utils.cache import patch_cache_control
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, mixins, permissions, status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from .models import CartoDBTable, GatewayType, Location
from .serializers import (
    CartoDBTableSerializer,
    GatewayTypeSerializer,
    LocationSerializer,
    LocationLightSerializer,
)


class CartoDBTablesView(ListAPIView):
    """
    Gets a list of CartoDB tables for the mapping system
    """
    queryset = CartoDBTable.objects.all()
    serializer_class = CartoDBTableSerializer
    permission_classes = (permissions.IsAdminUser,)


class LocationTypesViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    """
    Returns a list off all Location types
    """
    queryset = GatewayType.objects.all()
    serializer_class = GatewayTypeSerializer
    permission_classes = (permissions.IsAdminUser,)


class ETagMixin(object):

    def etag_cache_list(self, cls, *args, **kwargs):
        schema_name = connection.schema_name
        cache_etag = cache.get("{}-locations-etag".format(schema_name))
        request_etag = self.request.META.get("HTTP_IF_NONE_MATCH", None)

        local_etag = cache_etag if cache_etag else '"'+uuid.uuid4().hex+'"'

        if cache_etag and request_etag and cache_etag == request_etag:
            response = Response(status=status.HTTP_304_NOT_MODIFIED)
        else:
            response = super(cls, self).list(*args, **kwargs)
            response["ETag"] = local_etag

        if not cache_etag:
            cache.set("{}-locations-etag".format(schema_name), local_etag)

        patch_cache_control(response, private=True, must_revalidate=True)
        return response


class LocationsViewSet(ETagMixin,
                       mixins.RetrieveModelMixin,
                       mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.UpdateModelMixin,
                       viewsets.GenericViewSet):
    """
    CRUD for Locations
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    def list(self, *args, **kwargs):
        """
        Returns list of instances only if there's a new ETag, and it does not
        match the one sent along with the request.
        Otherwise it returns 304 NOT MODIFIED.
        """
        return self.etag_cache_list(LocationsViewSet, *args, **kwargs)

    def get_object(self):
        if "p_code" in self.kwargs:
            obj = get_object_or_404(self.get_queryset(), p_code=self.kwargs["p_code"])
            self.check_object_permissions(self.request, obj)
            return obj
        else:
            return super(LocationsViewSet, self).get_object()


class LocationsLightViewSet(ETagMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    """
    Returns a list of all Locations with restricted field set.
    """
    queryset = Location.objects.all()
    serializer_class = LocationLightSerializer

    def list(self, *args, **kwargs):
        """
        Returns list of instances only if there's a new ETag, and it does not
        match the one sent along with the request.
        Otherwise it returns 304 NOT MODIFIED.
        """
        return self.etag_cache_list(LocationsLightViewSet, *args, **kwargs)


class LocationQuerySetView(ListAPIView):
    model = Location
    serializer_class = LocationLightSerializer

    def get_queryset(self):
        q = self.request.query_params.get('q')
        qs = self.model.objects

        if q:
            qs = qs.filter(name__icontains=q)

        # return maximum 7 records
        return qs.all()[:7]


class LocationAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated():
            return Location.objects.none()

        qs = Location.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs