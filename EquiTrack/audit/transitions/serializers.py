from rest_framework import serializers


class EngagementCancelSerializer(serializers.Serializer):
    cancel_comment = serializers.CharField()