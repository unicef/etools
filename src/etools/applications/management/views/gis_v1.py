from django.db import connection
from django.db.models import Q

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from etools.applications.EquiTrack.permissions import IsSuperUser
from unicef_locations.models import Location
from etools.applications.management.serializers import (
    GisLocationWktSerializer,
    GisLocationListSerializer,
    GisLocationGeojsonSerializer
)
from etools.applications.partners.models import Intervention
from etools.applications.reports.models import AppliedIndicator
from etools.applications.t2f.models import TravelActivity
from etools.applications.users.models import Country


class GisLocationsInUseViewset(ListAPIView):
    model = Location
    serializer_class = GisLocationListSerializer
    permission_classes = (IsSuperUser,)

    def get(self, request):
        '''
        return the list of locations in use either in interventions or travels
         - a valid country_id is mandatory in the query string
        '''
        country_id = request.query_params.get('country_id')

        if not country_id:
            return Response(status=400, data={'error': 'Country id is required'})

        try:
            # we need to set the workspace before making any query
            connection.set_tenant(Country.objects.get(pk=country_id))
        except Country.DoesNotExist:
            return Response(status=400, data={'error': 'Country not found'})
        else:
            interventions = Intervention.objects.all()
            location_ids = set()

            for intervention in interventions:
                for loc in intervention.flat_locations.all():
                    location_ids.add(loc.id)

            indicators = AppliedIndicator.objects.prefetch_related(
                'locations'
            ).all()

            for indicator in indicators:
                for iloc in indicator.locations.all():
                    location_ids.add(iloc.id)

            travel_activities = TravelActivity.objects.prefetch_related(
                'locations'
            ).all()

            for travel_activity in travel_activities:
                for t2f_loc in travel_activity.locations.all():
                    location_ids.add(t2f_loc.id)

            locations = Location.objects.filter(
                pk__in=list(location_ids),
            ).all()

            serializer = GisLocationListSerializer(locations, many=True, context={'request': request})

            return Response(serializer.data)


class GisLocationsGeomListViewset(ListAPIView):
    permission_classes = (IsSuperUser,)

    def get_serializer_class(self):
        geo_format = self.request.query_params.get('geo_format') or 'geojson'

        if geo_format == 'geojson':
            return GisLocationGeojsonSerializer
        else:
            return GisLocationWktSerializer

    def get(self, request):
        '''
        return the list of locations with geometry
         - a valid country_id is mandatory in the query string
         - Optionals:
          - the geometry format in the response can be set with the 'geo_format' quqerystring param('wkt' or 'geojson')
          - filter results by geometry type(polygon or point). By default, return both geom type in the results.
        '''
        geo_format = self.request.query_params.get('geo_format') or 'geojson'
        geom_type = self.request.query_params.get('geom_type') or None

        if geo_format not in ['wkt', 'geojson']:
            return Response(status=400, data={'error': 'Invalid geometry format received'})

        if geom_type not in ['polygon', 'point', None]:
            return Response(status=400, data={'error': 'Invalid geometry type received'})

        country_id = request.query_params.get('country_id')

        if not country_id:
            return Response(status=400, data={'error': 'Country id is required'})

        try:
            # we need to set the workspace before making any query
            connection.set_tenant(Country.objects.get(pk=country_id))
        except Country.DoesNotExist:
            return Response(status=400, data={'error': 'Country not found'})
        else:
            if geo_format == 'geojson':
                if geom_type is None:
                    response = {
                        "type": "FeatureCollection",
                        # TODO: add srid to the FeatureCollection
                        # see https://github.com/djangonauts/django-rest-framework-gis/pull/113/files
                        # "crs": {},
                        "features": []
                    }

                    # we must specify the proper serializer `geo_field` for both points and polygons, to be able
                    # to generate a result which is importable in QGis
                    polygons = Location.objects.filter(geom__isnull=False).all()
                    self.get_serializer_class().Meta.geo_field = 'geom'
                    serialized_polygons = self.get_serializer(polygons, many=True, context={'request': request})

                    if len(serialized_polygons.data) > 0:
                        response["features"] += serialized_polygons.data["features"]

                    points = Location.objects.filter(point__isnull=False).all()
                    self.get_serializer_class().Meta.geo_field = 'point'
                    serialized_points = self.get_serializer(points, many=True, context={'request': request})

                    if len(serialized_points.data) > 0:
                        response["features"] += serialized_points.data["features"]

                    return Response(response)

                if geom_type == 'polygon':
                    locations = Location.objects.filter(geom__isnull=False).all()
                    self.get_serializer_class().Meta.geo_field = 'geom'
                elif geom_type == 'point':
                    locations = Location.objects.filter(point__isnull=False).all()
                    self.get_serializer_class().Meta.geo_field = 'point'
            else:
                if geom_type is None:
                    locations = Location.objects.filter(Q(geom__isnull=False) | Q(point__isnull=False)).all()
                elif geom_type == 'polygon':
                    locations = Location.objects.filter(geom__isnull=False).all()
                elif geom_type == 'point':
                    locations = Location.objects.filter(point__isnull=False).all()

            serializer = self.get_serializer(locations, many=True, context={'request': request})
            return Response(serializer.data)


class GisLocationsGeomDetailsViewset(RetrieveAPIView):
    permission_classes = (IsSuperUser,)

    def get_serializer_class(self):
        geo_format = self.request.query_params.get('geo_format') or 'geojson'

        if geo_format == 'geojson':
            return GisLocationGeojsonSerializer
        else:
            return GisLocationWktSerializer

    def get(self, request, id=None, pcode=None):
        '''
        return the details of a single location, either by ID or P_CODE
         - a valid country_id is mandatory in the query string
         - the geometry format in the response can be set with the 'geo_format' querystring variable('wkt' or 'geojson')
        '''
        geo_format = self.request.query_params.get('geo_format') or 'geojson'
        if geo_format not in ['wkt', 'geojson']:
            return Response(status=400, data={'error': 'Invalid geo format received'})

        country_id = self.request.query_params.get('country_id')

        if not country_id:
            return Response(status=400, data={'error': 'Country is required'})

        try:
            # we need to set the workspace before making any query
            connection.set_tenant(Country.objects.get(pk=country_id))
        except Country.DoesNotExist:
            return Response(status=400, data={'error': 'Country not found'})

        if pcode is not None or id is not None:
            try:
                lookup = {'p_code': pcode} if id is None else {'pk': id}
                location = Location.objects.get(**lookup)
            except Location.DoesNotExist:
                return Response(status=400, data={'error': 'Location not found'})
            else:
                # `geo_field` is mandatory if we use GeojsonSerializer
                if geo_format == 'geojson':
                    if location.geom:
                        self.get_serializer_class().Meta.geo_field = 'geom'
                    elif location.point:
                        self.get_serializer_class().Meta.geo_field = 'point'

                serializer = self.get_serializer(location, context={'request': request})
                return Response(serializer.data)
