from django.utils.translation import ugettext_lazy as _

from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer

from etools.applications.permissions_simplified.serializers import SafeReadOnlySerializerMixin


class FieldMonitoringGeneralAttachmentSerializer(SafeReadOnlySerializerMixin, BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code='fm_common')
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass
