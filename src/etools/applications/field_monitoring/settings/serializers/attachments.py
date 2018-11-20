from django.utils.translation import ugettext_lazy as _

from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer

from etools.applications.field_monitoring.settings.models.attachments import FieldMonitoringGeneralAttachment
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin


class FieldMonitoringGeneralAttachmentSerializer(PermissionsBasedSerializerMixin, BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code='fm_common')
    )

    class Meta(BaseAttachmentSerializer.Meta):
        model = FieldMonitoringGeneralAttachment
