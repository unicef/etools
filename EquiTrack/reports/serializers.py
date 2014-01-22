__author__ = 'jcranwellward'

from rest_framework import serializers

from .models import (
    Sector,
    Goal
)


class GoalSerializer(serializers.ModelSerializer):

    goal_id = serializers.CharField(source='id', read_only=True)
    sector_id = serializers.CharField(source='sector__id', read_only=True)

    class Meta:
        model = Goal
        fields = ('goal_id', 'name', 'description', 'sector_id')


class SectorSerializer(serializers.ModelSerializer):

    sector_id = serializers.CharField(source='id', read_only=True)
    goals = GoalSerializer()

    class Meta:
        model = Sector
        fields = ('sector_id', 'name', 'description', 'goals')

