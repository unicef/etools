from django.utils.translation import ugettext as _

from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer


class TPMPartnerAttachmentsSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(
        code="tpm_partner"), label=_('Document Type'))

    class Meta(BaseAttachmentSerializer.Meta):
        pass


class ActivityAttachmentsSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code="tpm"), label=_('Document Type'))

    class Meta(BaseAttachmentSerializer.Meta):
        fields = BaseAttachmentSerializer.Meta.fields + ['object_id']

    def create(self, validated_data):
        validated_data['code'] = 'activity_attachments'
        return super(ActivityAttachmentsSerializer, self).create(validated_data)


class ActivityReportSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code="tpm_report"), label=_('Document Type'))

    class Meta(BaseAttachmentSerializer.Meta):
        fields = BaseAttachmentSerializer.Meta.fields + ['object_id']

    def create(self, validated_data):
        validated_data['code'] = 'activity_report'
        return super(ActivityReportSerializer, self).create(validated_data)


class TPMVisitReportAttachmentsSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code='tpm_report_attachments'),
                                         label=_('Document Type'))

    class Meta(BaseAttachmentSerializer.Meta):
        pass

    def create(self, validated_data):
        validated_data['code'] = 'visit_report_attachments'
        return super().create(validated_data)


class TPMVisitAttachmentsSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code='tpm'),
                                         label=_('Document Type'))

    class Meta(BaseAttachmentSerializer.Meta):
        pass

    def create(self, validated_data):
        validated_data['code'] = 'visit_attachments'
        return super().create(validated_data)
