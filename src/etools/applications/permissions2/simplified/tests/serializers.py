from rest_framework import serializers

from etools.applications.permissions2.simplified.serializers import SafeReadOnlySerializerMixin
from etools.applications.permissions2.simplified.tests.models import Parent, Child


class ParentSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = serializers.ALL_FIELDS


class ChildSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = serializers.ALL_FIELDS
