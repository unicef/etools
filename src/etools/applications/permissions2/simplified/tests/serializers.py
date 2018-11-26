from rest_framework import serializers

from etools.applications.permissions2.simplified.serializers import SafeReadOnlySerializerMixin
from etools.applications.permissions2.simplified.tests.models import Parent, Child, ModelWithFSMField


class ParentSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = serializers.ALL_FIELDS


class ChildSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = serializers.ALL_FIELDS


class ModelWithFSMFieldSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ModelWithFSMField
        fields = serializers.ALL_FIELDS
