from __future__ import absolute_import, division, print_function, unicode_literals

from attachments.serializers_fields import FileTypeModelChoiceField
from attachments.models import FileType
from attachments.serializers import Base64AttachmentSerializer
from utils.writable_serializers.serializers import WritableNestedSerializerMixin


class TPMPartnerAttachmentsSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code="tpm_partner"))

    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        pass


class TPMAttachmentsSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code="tpm"))

    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        pass


class TPMReportSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code="tpm_report"))

    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        pass


class TPMReportAttachmentsSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code='tpm_report_attachments'))

    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        pass
