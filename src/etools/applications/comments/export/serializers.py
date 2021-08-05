from rest_framework import serializers
from unicef_restlib.fields import CommaSeparatedExportField


class CommentCSVSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    created = serializers.DateTimeField()
    user = serializers.CharField()
    state = serializers.CharField()
    users_related = CommaSeparatedExportField()
    related_to_description = serializers.CharField()
    related_to = serializers.CharField()
    text = serializers.CharField()
