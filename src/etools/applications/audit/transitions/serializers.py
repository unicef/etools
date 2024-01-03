
from rest_framework import serializers


class EngagementCancelSerializer(serializers.Serializer):
    cancel_comment = serializers.CharField()


class EngagementSendBackSerializer(serializers.Serializer):
    send_back_comment = serializers.CharField()
