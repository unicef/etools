__author__ = 'jcranwellward'

from rest_framework import serializers

from .models import (
    Sector,
    Goal,
    Indicator
)


class GoalSerializer(serializers.ModelSerializer):

    # TODO: ids are already readonly https://github.com/tomchristie/django-rest-framework/issues/2114#issuecomment-64095219
    goal_id = serializers.CharField(source='id', read_only=True)
    sector_id = serializers.CharField(source='sector.id', read_only=True)

    class Meta:
        model = Goal
        fields = ('goal_id', 'name', 'description', 'sector_id')


class SectorSerializer(serializers.ModelSerializer):

    sector_id = serializers.CharField(source='id', read_only=True)
    goals = GoalSerializer()

    class Meta:
        model = Sector
        fields = ('sector_id', 'name', 'description', 'goals')


class IndicatorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Indicator
        fields = ('id', 'name', 'unit', 'total', 'current', 'sector_total', 'sector_current')

