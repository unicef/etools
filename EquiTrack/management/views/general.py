from django.core.cache import cache
from django.db.models import F, Sum

from rest_framework.response import Response
from rest_framework.views import APIView

from EquiTrack.permissions import IsSuperUser
from funds.models import FundsReservationHeader
from users.models import Country

from vision.adapters.funding import FundReservationsSynchronizer
from vision.utils import comp_decimals


class InvalidateCache(APIView):
    permission_classes = (IsSuperUser,)

    def get(self, request, format=None):
        try:
            cache_key = request.query_params['key']

        except KeyError:
            return Response(status=400, data={'error': 'You must pass "key" as a query param'})

        cache.delete(cache_key)
        return Response({'success': 'key removed if it was present'})


class SyncFRs(APIView):
    permission_classes = (IsSuperUser,)

    def get(self, request, format=None):
        try:
            business_area = request.query_params['area']
        except KeyError:
            return Response(status=400, data={'error': 'You must pass "area" as a query param'})

        try:
            country = Country.objects.get(business_area_code=business_area)
        except Country.DoesNotExist:
            return Response(status=400, data={'error': 'Business Area code invalid'})

        FundReservationsSynchronizer(country).sync()

        return Response({'success': 'Funds Reservation sync for {} successfully performed'.format(country.name)})