from rest_framework import serializers

from etools.applications.audit_log.models import AuditLogEntry
from etools.applications.users.serializers import MinimalUserSerializer


class AuditLogEntrySerializer(serializers.ModelSerializer):
    user = MinimalUserSerializer(read_only=True)
    model_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLogEntry
        fields = (
            'id',
            'content_type',
            'object_id',
            'model_name',
            'action',
            'changed_fields',
            'old_values',
            'new_values',
            'user',
            'description',
            'created',
        )
        read_only_fields = fields

    def get_model_name(self, obj):
        return f'{obj.content_type.app_label}.{obj.content_type.model}'
