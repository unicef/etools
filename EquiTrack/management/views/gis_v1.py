from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import connection
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from EquiTrack.permissions import IsSuperUser
from t2f.models import TravelActivity
from users.models import Country
from partners.models import Intervention
from reports.models import AppliedIndicator
from locations.models import Location
from management.serializers import GisLocationListSerializer, GisLocationGeoDetailSerializer


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
    model = Location
    serializer_class = GisLocationGeoDetailSerializer
    permission_classes = (IsSuperUser,)

    def get(self, request):
        '''
        return the list of locations with geometry
         - a valid country_id is mandatory in the query string
         - the geometry format in the response can be set with the 'geo_format' querystring variable('wkt' or 'geojson')
        '''
        geo_format = self.request.query_params.get('geo_format') or 'geojson'
        if geo_format not in ['wkt', 'geojson']:
            return Response(status=400, data={'error': 'Invalid geo format received'})

        country_id = request.query_params.get('country_id')

        if not country_id:
            return Response(status=400, data={'error': 'Country id is required'})

        try:
            # we need to set the workspace before making any query
            connection.set_tenant(Country.objects.get(pk=country_id))
        except Country.DoesNotExist:
            return Response(status=400, data={'error': 'Country not found'})
        else:
            locations = Location.objects.filter(geom__isnull=False).all()
            serializer = GisLocationGeoDetailSerializer(locations, many=True, context={'request': request})

        return Response(serializer.data)


class GisLocationsGeomDetailsViewset(RetrieveAPIView):
    permission_classes = (IsSuperUser,)

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
                serializer = GisLocationGeoDetailSerializer(location, context={'request': request})
                return Response(serializer.data)
