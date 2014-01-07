__author__ = 'jcranwellward'

from rest_framework.generics import ListAPIView

from .models import Sector
from .serializers import SectorSerializer


class SectorView(ListAPIView):

    model = Sector
    serializer_class = SectorSerializer
