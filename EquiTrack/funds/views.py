__author__ = 'achamseddine'

from rest_framework import viewsets, mixins
from rest_framework.decorators import detail_route
from rest_framework import status
from rest_framework.response import Response

from .models import Donor, Grant
from .serializers import (
    DonorSerializer,
    GrantSerializer,
)


class DonorViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):

    queryset = Donor.objects.all()
    serializer_class = DonorSerializer

    @detail_route(methods=['get'], url_path='grants')
    def grants(self, request, pk=None):
        """
        Return all the Grants for this Donor
        """
        data = Grant.objects.filter(donor_id=pk).values()
        return Response(
            data,
            status=status.HTTP_200_OK,
        )


class GrantViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    """
    Returns a list of all Grants
    """
    queryset = Grant.objects.all()
    serializer_class = GrantSerializer