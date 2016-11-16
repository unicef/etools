__author__ = 'achamseddine'

from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser
from .models import (
    ResponsePlan,
    ResultType,
    Result,
    Milestone,
    Sector,
    Indicator,
    Unit
)
from .serializers import (
    ResponsePlanSerializer,
    ResultTypeSerializer,
    ResultSerializer,
    MilestoneSerializer,
    SectorCreateSerializer,
    IndicatorCreateSerializer,
    UnitSerializer
)


class ResponsePlanViewSet(mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    """
    Returns a list of all response plans
    """
    queryset = ResponsePlan.objects.all()
    serializer_class = ResponsePlanSerializer


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


class MilestoneViewSet(viewsets.ModelViewSet):
    """
    CRUD api for Milestones
    """
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer
    permission_classes = (IsAdminUser,)


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
