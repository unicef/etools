import json

from rest_framework import serializers

from snapshot.utils import create_change_dict, create_snapshot


class JsonFieldSerializer(serializers.Field):

    def to_representation(self, value):
        return json.loads(value) if isinstance(value, str) else value

    def to_internal_value(self, data):
        return json.dumps(data) if isinstance(data, dict) else data


class SnapshotModelSerializer(serializers.ModelSerializer):
    def save(self, **kwargs):
        data = dict(
            list(self.validated_data.items()) +
            list(kwargs.items())
        )
        change = create_change_dict(self.instance, data)

        super(SnapshotModelSerializer, self).save(**kwargs)
        create_snapshot(self.instance, self.context["request"].user, change)
        return self.instance
