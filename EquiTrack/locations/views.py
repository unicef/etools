__author__ = 'unicef-leb-inn'

from rest_framework.generics import ListAPIView

from .models import CartoDBTable
from .serializers import CartoDBTableSerializer


class CartoDBTablesView(ListAPIView):
    queryset = CartoDBTable.objects.all()
    serializer_class = CartoDBTableSerializer
