from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import mimetypes
import uuid
from collections import OrderedDict

from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers


class ModelChoiceField(serializers.PrimaryKeyRelatedField):
    default_error_messages = {
        'does_not_exist': _('Invalid option "{pk_value}" - option does not available.'),
    }

    @property
    def choices(self):
        if hasattr(self._choices, '__call__'):
            self._choices = self._choices()
        return self._choices

    def get_choice(self, obj):
        raise NotImplemented

    def _choices(self):
        return OrderedDict(map(self.get_choice, self.get_queryset()))


class FileTypeModelChoiceField(ModelChoiceField):
    def get_choice(self, obj):
        return obj.id, obj.label


class Base64FileField(serializers.FileField):
    def to_internal_value(self, data):
        if not isinstance(data, six.string_types):
            raise serializers.ValidationError(_('Incorrect base64 format.'))

        try:
            mime, encoded_data = data.replace('data:', '', 1).split(';base64,')
            extension = mimetypes.guess_extension(mime)
            content_file = ContentFile(base64.b64decode(encoded_data), name=str(uuid.uuid4()) + extension)

        except (ValueError, TypeError):
            raise serializers.ValidationError(_('Incorrect base64 format.'))

        return content_file


class AttachmentSingleFileField(serializers.RelatedField):
    def __init__(self, *args, **kwargs):
        # force attachment field to be read only
        # create/updates happen with separate api call request
        # we return the create/update link as part of the response
        kwargs["read_only"] = True
        super(AttachmentSingleFileField, self).__init__(*args, **kwargs)

    def get_attachment(self, instance):
        if hasattr(instance, self.source):
            attachment = getattr(instance, self.source)
            if attachment and attachment.last():
                return attachment.last()
        return None

    def get_attribute(self, instance):
        attachment = self.get_attachment(instance)
        return attachment.file if attachment is not None else None

    def to_representation(self, value):
        if not value:
            return None

        if not getattr(value, "url", None):
            return None

        url = value.url
        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class AttachmentUploadLinkField(AttachmentSingleFileField):
    def to_representation(self, instance):
        attachment = self.get_attachment(instance)
        if attachment is not None:
            return reverse(
                "attachments:upload",
                args=[attachment.last().pk]
            )
        return None
