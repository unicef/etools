
from rest_framework import serializers

from etools.applications.t2f.serializers.filters import SortFilterSerializer
from etools.applications.t2f.serializers.travel import ActionPointSerializer


class ActionPointSortFilterSerializer(SortFilterSerializer):
    SORT_BY_SERIALIZER = ActionPointSerializer


class ActionPointFilterBoxSerializer(serializers.Serializer):
    f_status = serializers.CharField(source='status', required=False)
    f_assigned_by = serializers.IntegerField(source='assigned_by__pk', required=False)
    f_person_responsible = serializers.IntegerField(source='person_responsible__pk', required=False)
