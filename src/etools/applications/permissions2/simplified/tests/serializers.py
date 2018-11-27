from rest_framework import serializers

from etools.applications.permissions2.simplified.serializers import SafeReadOnlySerializerMixin
from etools.applications.permissions2.simplified.tests.models import SimplifiedTestParent, SimplifiedTestChild, SimplifiedTestModelWithFSMField


class ParentSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SimplifiedTestParent
        fields = serializers.ALL_FIELDS


class ChildSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SimplifiedTestChild
        fields = serializers.ALL_FIELDS


class ModelWithFSMFieldSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SimplifiedTestModelWithFSMField
        fields = serializers.ALL_FIELDS
