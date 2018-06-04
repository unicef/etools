import json

from rest_framework import serializers


class HactValuesField(serializers.Field):
    def to_representation(self, obj):
        # in case obj still in json format attempt to extract
        try:
            obj = json.loads(obj)
        except (ValueError, TypeError):
            pass

        return "\n".join(
            ["{}: {}".format(x, obj[x]) for x in sorted(list(obj))]
        )


class TypeArrayField(serializers.Field):
    def get_attribute(self, obj):
        return obj

    def to_representation(self, obj):
        return ", ".join(obj.types)
