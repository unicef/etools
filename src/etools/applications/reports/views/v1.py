from django.db.models import Q

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.reports.models import CountryProgramme, Indicator, Result, ResultType, Section, Unit
from etools.applications.reports.serializers.v1 import (
    CountryProgrammeSerializer,
    IndicatorCreateSerializer,
    ResultFullSerializer,
    ResultSerializer,
    ResultTypeSerializer,
    SectionCreateSerializer,
    UnitSerializer,
)
from etools.libraries.djangolib.views import ExternalModuleFilterMixin


class ResultTypeViewSet(mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    Returns a list of all Result Types
    """
    queryset = ResultType.objects.all()
    serializer_class = ResultTypeSerializer


class SectionViewSet(ExternalModuleFilterMixin,
                     QueryStringFilterMixin,
                     mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    """
    Returns a list of all Sections
    """
    queryset = Section.objects.all()
    serializer_class = SectionCreateSerializer
    filters = (
        ('active', 'active'),
    )
    module2filters = {
        'tpm': [lambda user: Q(tpm_activities__tpm_visit__tpm_partner__organization=user.profile.organization)]
    }


class ResultViewSet(viewsets.ModelViewSet):
    """
    Returns a list of all Results
    """
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = (IsAdminUser,)

    @action(detail=True, methods=['get'], url_path='full')
    def full(self, request, *args, **kwargs):
        serializer = ResultFullSerializer(instance=self.get_object(), context={'request': self.request})
        return Response(serializer.data)


class IndicatorViewSet(viewsets.ModelViewSet):
    """
    CRUD api for Indicators
    """
    queryset = Indicator.objects.all()
    serializer_class = IndicatorCreateSerializer
    permission_classes = (IsAdminUser,)


class UnitViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  viewsets.GenericViewSet):
    """
    Returns a list of all Units
    """
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer


class CountryProgrammeRetrieveView(RetrieveAPIView):
    """
    Returns one Country Programme by pk
    """
    queryset = CountryProgramme.objects.all()
    serializer_class = CountryProgrammeSerializer


class CountryProgrammeListView(ListAPIView):
    """
    Returns a list of all Country Programmes
    """
    queryset = CountryProgramme.objects.all()
    serializer_class = CountryProgrammeSerializer
