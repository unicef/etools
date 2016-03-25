__author__ = 'achamseddine'

from rest_framework import viewsets, mixins


from .models import Donor, Grant
from .serializers import (
    DonorSerializer,
    GrantSerializer,
)


class DonorViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Donor.objects.all()
    serializer_class = DonorSerializer


class GrantViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Grant.objects.all()
    serializer_class = GrantSerializer