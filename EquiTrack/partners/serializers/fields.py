from __future__ import unicode_literals
from rest_framework import serializers


class TypeArrayField(serializers.Field):
    def get_attribute(self, obj):
        return obj

    def to_representation(self, obj):
        return ", ".join(obj.types)
