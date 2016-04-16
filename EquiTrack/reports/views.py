__author__ = 'achamseddine'

from rest_framework import viewsets, mixins
from .models import ResultStructure, ResultType, Result, Sector, Indicator, Unit
from .serializers import (
    ResultStructureSerializer,
    ResultTypeSerializer,
    ResultSerializer,
    SectorCreateSerializer,
    IndicatorCreateSerializer,
    UnitSerializer
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
#     queryset = Goal.objects.all()
#     serializer_class = GoalCreateSerializer


class ResultViewSet(mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    """
    Returns a list of all Results
    """
    queryset = Result.objects.all()
    serializer_class = ResultSerializer


class IndicatorViewSet(mixins.ListModelMixin,
                       viewsets.GenericViewSet):
    """
    Returns a list of all Indicators
    """
    queryset = Indicator.objects.all()
    serializer_class = IndicatorCreateSerializer


class UnitViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  viewsets.GenericViewSet):
    """
    Returns a list of all Units
    """
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
