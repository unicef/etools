from rest_framework import serializers

from workplan.models import (
    Label, Workplan, WorkplanProject,)


class WorkplanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workplan
        fields = ('id', 'status', 'country_programme', 'workplan_projects')


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = '__all__'


class WorkplanProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkplanProject
        fields = '__all__'
