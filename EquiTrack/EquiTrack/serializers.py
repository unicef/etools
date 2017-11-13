import json

from rest_framework import serializers
from snapshot.utils import create_dict_with_relations, create_snapshot


class JsonFieldSerializer(serializers.Field):

    def to_representation(self, value):
        return json.loads(value) if isinstance(value, str) else value

    def to_internal_value(self, data):
        return json.dumps(data) if isinstance(data, dict) else data


class SnapshotModelSerializer(serializers.ModelSerializer):
    def save(self, **kwargs):
        pre_save = create_dict_with_relations(self.instance)
        super(SnapshotModelSerializer, self).save(**kwargs)
        create_snapshot(self.instance, pre_save, self.context["request"].user)
        return self.instance
