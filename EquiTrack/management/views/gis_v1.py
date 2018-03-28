from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

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

    def get_queryset(self):
        country_id = self.request.query_params.get('country_id')

        if country_id:
            # we need to set the workspace before making any query
            connection.set_tenant(Country.objects.get(pk=country_id))

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

            qs = Location.objects.filter(
                pk__in=list(location_ids),
            )
        else:
            raise ValidationError("Country id is missing!")

        return qs


class GisLocationsGeomListViewset(ListAPIView):
    model = Location
    serializer_class = GisLocationGeoDetailSerializer
    permission_classes = (IsSuperUser,)

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
    permission_classes = (IsSuperUser,)

    def get(self, request, id=None, pcode=None):
        country_id = self.request.query_params.get('country_id')

        if country_id and (pcode is not None or id is not None):
            # we need to set the workspace before making any query
            connection.set_tenant(Country.objects.get(pk=country_id))

            lookup = {'p_code': pcode} if id is None else {'pk': id}
            location = get_object_or_404(Location, **lookup)

            serializer = GisLocationGeoDetailSerializer(location, context={'request': request})
            return Response(serializer.data)
        else:
            raise ValidationError("Some of the required request parameters are missing!")
