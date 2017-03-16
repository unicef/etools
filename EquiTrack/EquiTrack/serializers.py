import json

from rest_framework import serializers


class JsonFieldSerializer(serializers.Field):

    def to_representation(self, value):
        return json.loads(value) if isinstance(value, str) else value

    def to_internal_value(self, data):
        return json.dumps(data) if isinstance(data, dict) else data