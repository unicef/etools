from rest_framework import serializers


class StaticDataSerializer(serializers.Serializer):
    travel_types = serializers.ListField(child=serializers.CharField())
    travel_modes = serializers.ListField(child=serializers.CharField())
    action_point_statuses = serializers.ListField(child=serializers.CharField())
