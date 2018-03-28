from __future__ import absolute_import, division, print_function, unicode_literals

import types

from django.utils.translation import ugettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from attachments.models import Attachment, AttachmentFlat, FileType
from attachments.serializers_fields import (
    AttachmentSingleFileField,
    Base64FileField,
)


class BaseAttachmentsSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(BaseAttachmentsSerializer, self).validate(attrs)

        if not self.partial and bool(data.get('file')) == bool(data.get('hyperlink')):
            raise ValidationError(_('Please provide file or hyperlink.'))

        if self.partial and 'file' in data and not data['file']:
            raise ValidationError(_('Please provide file or hyperlink.'))

        if self.partial and 'link' in data and not data['link']:
            raise ValidationError(_('Please provide file or hyperlink.'))

        return data

    class Meta:
        model = Attachment
        fields = [
            'id',
            'file_type',
            'file',
            'hyperlink',
            'created',
            'modified',
            'uploaded_by',
        ]
        extra_kwargs = {
            'created': {
                'label': _('Date Uploaded'),
            },
        }


class Base64AttachmentSerializer(BaseAttachmentsSerializer):
    file = Base64FileField(required=False, label=_('File Attachment'))
    file_name = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        data = super(Base64AttachmentSerializer, self).validate(attrs)
        file_name = data.pop('file_name', None)
        if 'file' in data and file_name:
            data['file'].name = file_name
        return data

    class Meta(BaseAttachmentsSerializer.Meta):
        fields = BaseAttachmentsSerializer.Meta.fields + ['file_name', ]


class AttachmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="attachment.pk")
    filename = serializers.CharField(source="attachment.filename")

    class Meta:
        model = AttachmentFlat
        exclude = ("attachment", )


class AttachmentFileUploadSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Attachment
        fields = ["file", "uploaded_by"]


def validate_attachment(cls, data):
    """We expect the attachment pk to be part of the data provided

    The attachment may be empty of content data, in that case
    we are attempting to associate this attachment with the instance,
    which may not exist at the moment.
    If instance does exist, then we can set the content data on the attachment.

    If we do have content data on the attachment, then we expect the instance
    to exist and that it matches that of the attachment.

    We expect the attachment to be updated/saved during the save method,
    so we set the data here, and leave it to be saved later.

    Backward compatibility:
    If we are provided with a valid then we expect it to be valid
    If no value provided, then we assume still working the old way
    """
    value, code = data

    try:
        attachment = Attachment.objects.get(pk=int(value))
    except Attachment.DoesNotExist:
        raise serializers.ValidationError("Attachment does not exist")

    file_type = FileType.objects.get(code=code)
    if attachment.content_object is not None:
        if not cls.instance or attachment.content_object != cls.instance:
            # If content object exists, expect instance to exist
            # as we're not able to re-purpose the attachment
            # Make sure content object matches instance
            raise serializers.ValidationError(
                "Attachment is already associated: {}".format(
                    attachment.content_object
                )
            )

    attachment.file_type = file_type
    attachment.code = code

    return attachment


class AttachmentSerializerMixin(object):
    def __init__(self, *args, **kwargs):
        super(AttachmentSerializerMixin, self).__init__(*args, **kwargs)
        self.attachment_list = []
        self.check_attachment_fields()

    def check_attachment_fields(self):
        """If we have a attachment type field

        Then we want to setup validation and save handling
        As attachments are not a field on the object, but rather
        related by way of content type.
        """
        for field_name, field in self.fields.items():
            if isinstance(field, serializers.ListSerializer):
                if hasattr(field.child, "field"):
                    for child_name, child in field.child.field.items():
                        self.handle_attachment_field(child, child_name)
            else:
                self.handle_attachment_field(field, field_name)

    def handle_attachment_field(self, field, field_name):
        if isinstance(field, AttachmentSingleFileField):
            # TODO once attachment flow used throughout
            # we can remove this check on initial data
            # and setting of read only flag, if no matching
            # attachment data
            if hasattr(self, "initial_data"):
                if field_name in self.initial_data:
                    # TODO remove this once using attachment flow
                    # if we override another field
                    # mark the otherfield as read only
                    if field.override is not None:
                        if field.override in self.fields:
                            self.fields[field.override].read_only = True
                    setattr(
                        self,
                        "validate_{}".format(field_name),
                        types.MethodType(validate_attachment, self)
                    )
                    self.attachment_list.append(field.source)
                else:
                    setattr(field, "read_only", True)

    def save(self, *args, **kwargs):
        """Attachments are not a relation on the object,

        So we need to remove them from the validated data list
        and then save them individually.
        The attachment objects were setup/created in the validation method
        """
        attachments_to_save = []
        for attachment_attr in self.attachment_list:
            attachments_to_save.append(
                self.validated_data.pop(attachment_attr)
            )
        response = super(AttachmentSerializerMixin, self).save(*args, **kwargs)
        for attachment in attachments_to_save:
            if attachment.content_object is None:
                attachment.content_object = self.instance
            attachment.save()
        return response
