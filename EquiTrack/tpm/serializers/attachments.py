from __future__ import absolute_import

from attachments.serializers_fields import FileTypeModelChoiceField
from attachments.models import FileType
from attachments.serializers import Base64AttachmentSerializer
from utils.writable_serializers.serializers import WritableNestedSerializerMixin


class TPMActivityPDSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        fields = ['id', 'file', 'file_name', 'hyperlink', 'created', 'modified', ]

    def validate(self, data):
        validated_data = super(TPMActivityPDSerializer, self).validate(data)
        validated_data['file_type'] = FileType.objects.get_or_create(
            code='tpm_pd',
            defaults={
                'name': 'Programme Documents',
                'order': 0,
            }
        )[0]
        return validated_data


class TPMAttachmentsSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code="tpm"))

    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        pass


class TPMReportAttachmentsSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code="tpm_report"))

    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        pass
