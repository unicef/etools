__author__ = 'unicef-leb-inn'

from rest_framework.generics import ListAPIView

from .models import CartoDBTable
from .serializers import CartoDBTableSerializer


class CartoDBTablesView(ListAPIView):
    """
    Gets a list of CartoDB tables for the mapping system
    """
    queryset = CartoDBTable.objects.all()
    serializer_class = CartoDBTableSerializer
