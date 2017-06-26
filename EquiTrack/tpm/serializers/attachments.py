from __future__ import absolute_import

from attachments.serializers_fields import FileTypeModelChoiceField
from attachments.models import FileType
from attachments.serializers import BaseAttachmentsSerializer


class TPMAttachmentsSerializer(BaseAttachmentsSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code="tpm"))

    class Meta(BaseAttachmentsSerializer.Meta):
        pass
