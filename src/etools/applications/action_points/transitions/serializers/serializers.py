from rest_framework import serializers


class ActionPointCompleteSerializer(serializers.Serializer):
    completed_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
