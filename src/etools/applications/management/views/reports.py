from django.utils import six

from rest_framework.response import Response
from rest_framework.views import APIView

from etools.applications.EquiTrack.permissions import IsSuperUser
from etools.applications.EquiTrack.utils import set_country
from etools.applications.users.models import Country as Workspace
from etools.applications.vision.adapters.programme import ProgrammeSynchronizer


class LoadResultStructure(APIView):
    permission_classes = (IsSuperUser,)

    def get(self, request, format=None):
        try:
            workspace = Workspace.objects.get(name=request.query_params.get('country').title())
        except (Workspace.DoesNotExist, AttributeError):
            return Response(status=400, data={'error': 'Country not found'})

        try:
            p = ProgrammeSynchronizer(workspace)
            p.sync()
        except BaseException as e:
            set_country(request.user, request)
            return Response(status=500, data=six.text_type(e))

        set_country(request.user, request)
        return Response({'success': 'Country = {}'.format(workspace.name)})
