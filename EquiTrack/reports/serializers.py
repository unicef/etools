

from rest_framework import serializers

from users.serializers import UserProfileSerializer
from workplan.serializers import ResultWorkplanPropertySerializer
from workplan.models import ResultWorkplanProperty
from .models import (
    ResultStructure,
    ResultType,
    Unit,
    Sector,
    Goal,
    Indicator,
    Result,
    CountryProgramme
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


class OutputSerializer(serializers.ModelSerializer):

    class Meta:
        model = Result
        fields = ('id', 'name', 'sector', 'humanitarian_tag')


class SectorCreateSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Sector
        fields = '__all__'





class IndicatorCreateSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Indicator
        fields = '__all__'


class ResultSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    workplan_properties = ResultWorkplanPropertySerializer(many=True)

    class Meta:
        model = Result
        fields = '__all__'

    def create(self, validated_data):
        workplan_properties = validated_data.pop("workplan_properties")
        result = Result.objects.create(**validated_data)
        for workplan_property in workplan_properties:
            ResultWorkplanProperty.objects.create(result=result, **workplan_property)
        return result


class ResultStructureSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = ResultStructure
        fields = '__all__'


class ResultTypeSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = ResultType
        fields = '__all__'


class UnitSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Unit
        fields = '__all__'


class CountryProgrammeSerializer(serializers.ModelSerializer):

    class Meta:
        model = CountryProgramme
        fields = '__all__'