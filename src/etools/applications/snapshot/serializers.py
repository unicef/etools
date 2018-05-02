
from rest_framework import serializers

from etools.applications.snapshot.models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = "__all__"
