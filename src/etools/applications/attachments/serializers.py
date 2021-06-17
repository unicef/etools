from django.utils.translation import gettext_lazy as _

from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer


class CodedAttachmentSerializer(BaseAttachmentSerializer):
    file_group = None
    code = None

    file_type = FileTypeModelChoiceField(
        queryset=FileType.objects.group_by(file_group),
        label=_('Document Type'),
    )

    class Meta(BaseAttachmentSerializer.Meta):
        fields = BaseAttachmentSerializer.Meta.fields + ['object_id']

    def create(self, validated_data):
        validated_data['code'] = self.code
        return super().create(validated_data)
