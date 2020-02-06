from typing import Any

from django.utils.translation import ugettext_lazy as _

from unicef_attachments.models import Attachment

from etools.applications.offline.errors import ValidationError
from etools.applications.offline.fields.simple_typed import TextField
from etools.applications.offline.metadata import Metadata
from etools.applications.offline.tasks import download_remote_attachment


class FileField(TextField):
    input_type = 'file'

    def get_attachment(self, value: str) -> Attachment:
        raise NotImplementedError

    def validate_single_value(self, value: Any, metadata: Metadata) -> Attachment:
        return self.get_attachment(super().validate_single_value(value, metadata))


class UploadedFileField(FileField):
    def get_attachment(self, value: str) -> Attachment:
        try:
            return Attachment.objects.get(id=value)
        except Attachment.DoesNotExist:
            raise ValidationError(_(f'Unable to find attachment by id {value}'))


class RemoteFileField(FileField):
    def get_attachment(self, value: str) -> Attachment:
        attachment = Attachment.objects.create(hyperlink=value)
        download_remote_attachment.delay(attachment.id, value)
        return attachment
