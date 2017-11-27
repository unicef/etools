from rest_framework import serializers

from workplan.models import (
    Workplan, WorkplanProject,)


class WorkplanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workplan
        fields = ('id', 'status', 'country_programme', 'workplan_projects')


class WorkplanProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkplanProject
        fields = '__all__'
