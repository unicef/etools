from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response

from vision.adapters.programme import ProgrammeSynchronizer, ProgrammeVisionParser
from management.permissions import IsSuperUser
from users.models import Country as Workspace
from EquiTrack.utils import set_country


class LoadResultStructure(APIView):
    permission_classes = (IsSuperUser,)

    def get(self, request, format=None):
        try:
            workspace = Workspace.objects.get(name=request.query_params.get('country').title())
        except Workspace.DoesNotExist:
            return Response(status=400, data={'error': 'Country not found'})

        try:
            #p = ProgrammeSynchronizer(workspace)
            p = ProgrammeVisionParser(workspace)
            p.sync()
        except BaseException as e:
            set_country(request.user, request)
            return Response(status=500, data=e)

        set_country(request.user, request)
        return Response({'success': 'Country = {}'.format(workspace.name)})