from django.utils.translation import gettext as _

from rest_framework import mixins, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.viewsets import GenericViewSet

from etools.applications.last_mile import models
from etools.applications.last_mile.admin import serializers
from etools.applications.last_mile.permissions import IsIPLMEditor

from etools.applications.last_mile.admin.serializers import (
    PointOfInterestAdminSerializer,
    UserAdminCreateSerializer,
    UserAdminSerializer,
    UserAdminUpdateSerializer,
)
from django.contrib.auth import get_user_model
from rest_framework.generics import ListCreateAPIView

from rest_framework.pagination import PageNumberPagination

class CustomDynamicPageNumberPagination(PageNumberPagination):
    page_size = 5  
    page_size_query_param = 'page_size'
    max_page_size = 100

class UserViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin, 
                  mixins.UpdateModelMixin,    
                  viewsets.GenericViewSet):
    permission_classes = [IsIPLMEditor]
    pagination_class = CustomDynamicPageNumberPagination

    queryset = get_user_model().objects.all().order_by('id')

    filter_backends = (SearchFilter,)
    search_fields = ('email', 'first_name', 'last_name', 'profile__organization__name', 'profile__organization__vendor_number')

    def get_serializer_class(self):

        if self.action in ['update', 'partial_update']:
            return UserAdminUpdateSerializer
        if self.action == 'create':
            return UserAdminCreateSerializer
        return UserAdminSerializer

class LocationsViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsIPLMEditor]
    serializer_class = serializers.PointOfInterestAdminSerializer
    pagination_class = CustomDynamicPageNumberPagination

    queryset = models.PointOfInterest.objects.all().order_by('id')

    # filter_backends = (SearchFilter,)