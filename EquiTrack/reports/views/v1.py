
from rest_framework import viewsets, mixins
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.permissions import IsAdminUser
from reports.models import (
    ResultStructure,
    ResultType,
    Result,
    Sector,
    Indicator,
    Unit,
    CountryProgramme
)
from reports.serializers.v1 import (
    ResultStructureSerializer,
    ResultTypeSerializer,
    ResultSerializer,
    SectorCreateSerializer,
    IndicatorCreateSerializer,
    UnitSerializer,
    CountryProgrammeSerializer
)


class ResultStructureViewSet(mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """
    Returns a list of all Result Structures
    """
    queryset = ResultStructure.objects.all()
    serializer_class = ResultStructureSerializer


class ResultTypeViewSet(mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    Returns a list of all Result Types
    """
    queryset = ResultType.objects.all()
    serializer_class = ResultTypeSerializer


class SectorViewSet(mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    mixins.CreateModelMixin,
                    viewsets.GenericViewSet):
    """
    Returns a list of all Sectors
    """
    queryset = Sector.objects.all()
    serializer_class = SectorCreateSerializer


# class GoalViewSet(mixins.RetrieveModelMixin,
#                   mixins.ListModelMixin,
#                   mixins.CreateModelMixin,
#                   viewsets.GenericViewSet):
#     """
#     Return a list of all Goals (CCCs)
#     """
#
#     queryset = Goal.objects.all()
#     serializer_class = GoalCreateSerializer


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
