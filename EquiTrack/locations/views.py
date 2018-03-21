from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from dal import autocomplete
from django.db import connection
from rest_framework import mixins, permissions, viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from EquiTrack.utils import etag_cached
from t2f.models import TravelActivity
from users.models import Country
from partners.models import Intervention
from locations.models import CartoDBTable, GatewayType, Location
from locations.serializers import (
    CartoDBTableSerializer,
    GatewayTypeSerializer,
    LocationLightSerializer,
    LocationSerializer,
    GisLocationListSerializer,
    GisLocationGeoDetailSerializer,
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


class LocationsViewSet(mixins.RetrieveModelMixin,
                       mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.UpdateModelMixin,
                       viewsets.GenericViewSet):
    """
    CRUD for Locations
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    @etag_cached('locations')
    def list(self, request, *args, **kwargs):
        return super(LocationsViewSet, self).list(request, *args, **kwargs)

    def get_object(self):
        if "p_code" in self.kwargs:
            obj = get_object_or_404(self.get_queryset(), p_code=self.kwargs["p_code"])
            self.check_object_permissions(self.request, obj)
            return obj
        else:
            return super(LocationsViewSet, self).get_object()

    def get_queryset(self):
        queryset = Location.objects.all()
        if "values" in self.request.query_params.keys():
            # Used for ghost data - filter in all(), and return straight away.
            try:
                ids = [int(x) for x in self.request.query_params.get("values").split(",")]
            except ValueError:
                raise ValidationError("ID values must be integers")
            else:
                queryset = queryset.filter(id__in=ids)
        return queryset


class LocationsLightViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Returns a list of all Locations with restricted field set.
    """
    queryset = Location.objects.all()
    serializer_class = LocationLightSerializer

    @etag_cached('locations')
    def list(self, request, *args, **kwargs):
        return super(LocationsLightViewSet, self).list(request, *args, **kwargs)


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


class GisLocationsInUseViewset(ListAPIView):
    model = Location
    serializer_class = GisLocationListSerializer
    permission_classes = (permissions.IsAdminUser,)

    def get_queryset(self):
        country_id = self.request.query_params.get('country_id')

        if country_id:
            # we need to set the workspace before making any query
            connection.set_tenant(Country.objects.get(pk=country_id))

            interventions = Intervention.objects.all()
            location_ids = []

            for intervention in interventions:
                flat_locations = set(intervention.flat_locations.all())

                ll_locations = set()
                for lower_result in intervention.all_lower_results:
                    for applied_indicator in lower_result.applied_indicators.all():
                        for location in applied_indicator.locations.all():
                            ll_locations.add(location)

                for loc in flat_locations | ll_locations:
                    location_ids.append(loc.id)

            travel_locations = TravelActivity.objects.prefetch_related(
                'locations'
            ).all()

            for t2f_loc in travel_locations:
                location_ids.append(t2f_loc.id)

            qs = Location.objects.filter(
                pk__in=location_ids,
                # geom__isnull=False,
            )

            '''
            print ""
            print qs.count()
            print len(location_ids)
            print ""
            '''
        else:
            raise ValidationError("Country id is missing!")

        return qs


class GisLocationsGeomListViewset(ListAPIView):
    model = Location
    serializer_class = GisLocationGeoDetailSerializer
    permission_classes = (permissions.IsAdminUser,)

    def get_queryset(self):
        country_id = self.request.query_params.get('country_id')

        if country_id:
            # we need to set the workspace before making any query
            connection.set_tenant(Country.objects.get(pk=country_id))

            qs = Location.objects.filter(geom__isnull=False)
        else:
            raise ValidationError("Country id is missing!")

        return qs


class GisLocationsGeomDetailsViewset(RetrieveAPIView):
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, id=None, pcode=None):
        country_id = self.request.query_params.get('country_id')

        if country_id:
            # we need to set the workspace before making any query
            connection.set_tenant(Country.objects.get(pk=country_id))

            lookup = {'p_code': pcode} if id is None else {'pk': id}
            location = get_object_or_404(Location, **lookup)

            serializer = GisLocationGeoDetailSerializer(location, context={'request': request})
            return Response(serializer.data)
        else:
            raise ValidationError("Some of the required request parameters are missing!")
