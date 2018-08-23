from rest_framework import mixins, viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from etools.applications.partners.views.v2 import choices_to_json_ready
from etools.applications.reports.models import CountryProgramme, Indicator, Result, Section, Unit
from etools.applications.reports.serializers.v1 import (
    CountryProgrammeSerializer,
    IndicatorCreateSerializer,
    ResultSerializer,
    SectionCreateSerializer,
    UnitSerializer,
)


class ResultTypeView(APIView):
    """Returns a list of all Result Types"""
    def get(self, request):
        return Response(
            choices_to_json_ready(Result.RESULT_TYPE_CHOICE)
        )


class SectionViewSet(mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     mixins.CreateModelMixin,
                     viewsets.GenericViewSet):
    """
    Returns a list of all Sections
    """
    queryset = Section.objects.all()
    serializer_class = SectionCreateSerializer


class ResultViewSet(viewsets.ModelViewSet):
    """
    Returns a list of all Results
    """
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = (IsAdminUser,)


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
