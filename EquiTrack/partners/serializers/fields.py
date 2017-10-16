from __future__ import unicode_literals

from rest_framework import serializers


class HactValuesField(serializers.Field):
    def to_representation(self, obj):
        return "\n".join(
            ["{}: {}".format(x, obj[x]) for x in sorted(list(obj))]
        )


class TypeArrayField(serializers.Field):
    def get_attribute(self, obj):
        return obj

    def to_representation(self, obj):
        return ", ".join(obj.types)
