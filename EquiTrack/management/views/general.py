from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.response import Response

from EquiTrack.permissions import IsSuperUser


class InvalidateCache(APIView):
    permission_classes = (IsSuperUser,)

    def get(self, request, format=None):
        try:
            cache_key = request.query_params['key']

        except KeyError:
            return Response(status=400, data={'error': 'You must pass "key" as a query param'})

        cache.delete(cache_key)
        return Response({'success': 'key removed if it was present'})
