import base64
import mimetypes
import uuid
from collections import OrderedDict

from django.core.files.base import ContentFile
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
        return obj.id, obj.name


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
