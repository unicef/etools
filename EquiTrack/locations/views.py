__author__ = 'unicef-leb-inn'

from rest_framework.generics import ListAPIView

from locations.models import CartoDBTable


class CartoDBTablesView(ListAPIView):
    model = CartoDBTable
