from django.db import connection
from django.db.models import Q

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from unicef_restlib.permissions import IsSuperUser

from etools.applications.activities.models import Activity
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.locations.models import Location
from etools.applications.management.serializers import (
    GisLocationGeojsonSerializer,
    GisLocationListSerializer,
    GisLocationWktSerializer,
)
from etools.applications.t2f.models import TravelActivity
from etools.applications.users.models import Country


class GisLocationsInUseViewset(ListAPIView):
    model = Location
    serializer_class = GisLocationListSerializer
    permission_classes = (IsSuperUser,)

    def get(self, request):
        """
        return the list of locations in use either in interventions or travels
         - a valid country_id is mandatory in the query string
        """
        country_id = request.query_params.get('country_id')

        if not country_id:
            return Response(status=400, data={'error': 'Country id is required'})

        try:
            # we need to set the workspace before making any query
            connection.set_tenant(Country.objects.get(pk=country_id))
        except Country.DoesNotExist:
            return Response(status=400, data={'error': 'Country not found'})
        else:
            locs = Location.objects.all_with_geom().filter(Q(intervention_flat_locations__isnull=False) |
                                                           Q(applied_indicators__isnull=False) |
                                                           Q(actionpoint__isnull=False))\
                .values_list("id", flat=True).distinct()

            t2f_locs = TravelActivity.objects.exclude(locations__isnull=True).values_list(
                "locations", flat=True).distinct()

            tpm_activity_locs = Activity.objects.exclude(locations__isnull=True).values_list(
                "locations", flat=True).distinct()

            monitoring_activity_locs = MonitoringActivity.objects.exclude(location__isnull=True).values_list(
                "location_id", flat=True)

            all_locs = set(locs) | set(t2f_locs) | set(tpm_activity_locs) | set(monitoring_activity_locs)

            locations = Location.objects.all_with_geom().filter(
                pk__in=list(all_locs),
            )

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
        """
        return the list of locations with geometry
            - a valid country_id is mandatory in the query string
            - Optionals:
            - the geom type of the response can be set with the 'geo_format' GET param( can be 'wkt' or 'geojson')
            - filter results by geometry type(polygon or point). By default, return both geom type in the results.
            - filter active/archived/all locations with the `status` param
        """
        geo_format = self.request.query_params.get('geo_format') or 'geojson'
        geom_type = self.request.query_params.get('geom_type') or None
        loc_status = self.request.query_params.get('status').lower() if 'status' in self.request.query_params else None

        if geo_format not in ['wkt', 'geojson']:
            return Response(
                status=400,
                data={'error': 'Invalid geometry format received, `wkt` or `geojson` expected.'}
            )

        if geom_type not in ['polygon', 'point', None]:
            return Response(
                status=400,
                data={'error': 'Invalid geometry type received, `polygon` or `point` expected.'}
            )

        if loc_status not in ['active', 'archived', 'all', None]:
            return Response(
                status=400,
                data={'error': 'Invalid location status code received, `active`, `archived` or `all` expected.'}
            )

        country_id = request.query_params.get('country_id')

        if loc_status == 'active':
            location_queryset = Location.objects.all_with_geom().filter(is_active=True)
        elif loc_status == 'archived':
            location_queryset = Location.objects.all_with_geom().filter(is_active=False)
        else:
            location_queryset = Location.objects.all_with_geom().all()

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
                    # `point__isnull = True` = polygons(`geom__isnull=False`) + locations with no geometry at all
                    polygons = location_queryset.filter(point__isnull=True)
                    self.get_serializer_class().Meta.geo_field = 'geom'
                    serialized_polygons = self.get_serializer(polygons, many=True, context={'request': request})

                    if len(serialized_polygons.data) > 0:
                        response["features"] += serialized_polygons.data["features"]

                    points = location_queryset.filter(point__isnull=False)
                    self.get_serializer_class().Meta.geo_field = 'point'
                    serialized_points = self.get_serializer(points, many=True, context={'request': request})

                    if len(serialized_points.data) > 0:
                        response["features"] += serialized_points.data["features"]

                    return Response(response)

                if geom_type == 'polygon':
                    locations = location_queryset.filter(geom__isnull=False)
                    self.get_serializer_class().Meta.geo_field = 'geom'
                elif geom_type == 'point':
                    locations = location_queryset.filter(point__isnull=False)
                    self.get_serializer_class().Meta.geo_field = 'point'
            else:
                if geom_type is None:
                    locations = location_queryset.all()
                elif geom_type == 'polygon':
                    locations = location_queryset.filter(geom__isnull=False)
                elif geom_type == 'point':
                    locations = location_queryset.filter(point__isnull=False)

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
        """
        return the details of a single location, either by ID or P_CODE
         - a valid country_id is mandatory in the query string
         - the geometry format in the response can be set with the 'geo_format' querystring variable('wkt' or 'geojson')
        """
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
                location = Location.objects.all_with_geom().get(**lookup)
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
