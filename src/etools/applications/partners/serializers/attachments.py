from rest_framework import serializers
from unicef_attachments.models import FileType


class PMPAttachmentFileTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileType
        fields = [
            'id',
            'name',
            'label',
        ]
