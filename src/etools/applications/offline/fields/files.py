from typing import Any

from django.db import connection, transaction
from django.utils.translation import gettext_lazy as _

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


def _get_uploaded_attachment(value: str) -> Attachment:
    try:
        return Attachment.objects.get(id=value)
    except Attachment.DoesNotExist:
        raise ValidationError(_(f'Unable to find attachment by id {value}'))


class UploadedFileField(FileField):
    def get_attachment(self, value: str) -> Attachment:
        return _get_uploaded_attachment(value)


def _get_remote_attachment(value: str) -> Attachment:
    attachment = Attachment.objects.create(hyperlink=value)
    transaction.on_commit(
        lambda: download_remote_attachment.delay(connection.tenant.schema_name, attachment.id, value)
    )
    return attachment


class RemoteFileField(FileField):
    def get_attachment(self, value: str) -> Attachment:
        return _get_remote_attachment(value)


class MixedUploadedRemoteFileField(FileField):
    """
    Mixed file field for 100% reuse blueprint for offline/online data collection.
    If value contains `http`, download file and make new attachment. Else search attachment by id
    """

    def get_attachment(self, value: str) -> Attachment:
        if 'http' in value:
            return _get_remote_attachment(value)
        else:
            return _get_uploaded_attachment(value)
