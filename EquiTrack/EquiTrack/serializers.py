from rest_framework import serializers


class JSONField(serializers.Field):
    def to_internal_value(self, data):

        pass
    def to_representation(self, value):

        pass

