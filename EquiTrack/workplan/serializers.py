from rest_framework import serializers

from workplan.models import (
    Workplan, )


class WorkplanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workplan
        fields = ('id', 'status', 'country_programme', 'workplan_projects')
