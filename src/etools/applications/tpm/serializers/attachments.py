
from django.utils.translation import ugettext as _

from etools.applications.attachments.models import FileType
from etools.applications.attachments.serializers import BaseAttachmentSerializer
from etools.applications.attachments.serializers_fields import FileTypeModelChoiceField


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
