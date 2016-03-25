__author__ = 'achamseddine'

from rest_framework import viewsets, mixins
from .models import ResultStructure, ResultType, Result, Sector, Goal, Indicator, Unit
from .serializers import (
    ResultStructureSerializer,
    ResultTypeSerializer,
    ResultSerializer,
    SectorCreateSerializer,
    GoalCreateSerializer,
    IndicatorCreateSerializer,
    UnitSerializer
)


class ResultStructureViewSet(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            mixins.CreateModelMixin,
                            viewsets.GenericViewSet):

    queryset = ResultStructure.objects.all()
    serializer_class = ResultStructureSerializer


class ResultTypeViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = ResultType.objects.all()
    serializer_class = ResultTypeSerializer


class SectorViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Sector.objects.all()
    serializer_class = SectorCreateSerializer


class GoalViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Goal.objects.all()
    serializer_class = GoalCreateSerializer


class OutputViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Result.objects.all()
    serializer_class = ResultSerializer


class IndicatorViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Indicator.objects.all()
    serializer_class = IndicatorCreateSerializer


class UnitViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
