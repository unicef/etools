from __future__ import absolute_import, division, print_function, unicode_literals

from six.moves import urllib_parse

from django.utils.translation import ugettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from attachments.models import Attachment, FileType
from attachments.serializers_fields import (
    AttachmentSingleFileField,
    AttachmentUploadLinkField,
    Base64FileField,
)
from utils.common.urlresolvers import site_url


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


class AttachmentSerializer(BaseAttachmentsSerializer):
    created = serializers.DateTimeField(format='%d %b %Y')
    file_type = serializers.CharField(source='file_type.label')
    url = serializers.SerializerMethodField()
    filename = serializers.CharField()

    class Meta(BaseAttachmentsSerializer.Meta):
        fields = [
            'created', 'file_type', 'url', 'filename', 'uploaded_by'
        ]

    def get_url(self, obj):
        return urllib_parse.urljoin(site_url(), obj.url)


class AttachmentFileUploadSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Attachment
        fields = ["file", "uploaded_by"]


class AttachmentSerializerMixin(object):
    ATTACHMENT_SUFFIX = "_upload_link"

    def __init__(self, *args, **kwargs):
        super(AttachmentSerializerMixin, self).__init__(*args, **kwargs)
        if self.instance:
            self.handle_upload_links()

    def get_upload_field_name(self, field_name):
        """Ensure we get valid field name
        Need to prevent field being added mutliple times with
        suffix appended each time
        """
        if not field_name.endswith(self.ATTACHMENT_SUFFIX):
            upload_name = "{}{}".format(field_name, self.ATTACHMENT_SUFFIX)
            if upload_name not in self.fields.keys():
                return upload_name
        return None

    def handle_upload_links(self):
        # if request is post, put, or patch
        # check if attachment field types exist
        # ensure attachment record exists for instance
        # set upload link value
        if self.context["request"].method in ["PATCH", "POST", "PUT"]:
            for field_name, field in self.fields.items():
                if isinstance(field, serializers.ListSerializer):
                    for child_name, child in field.child.fields.items():
                        self.add_upload_links(
                            self.fields[field_name].child.fields,
                            field.child.instance,
                            child,
                            child_name
                        )
                else:
                    self.add_upload_links(
                        self.fields,
                        self.instance,
                        field,
                        field_name
                    )

    def add_upload_links(self, fields, instance, field, field_name):
        if isinstance(field, AttachmentSingleFileField):
            upload_field_name = self.get_upload_field_name(field_name)
            if upload_field_name is not None:
                if instance is not None:
                    attachments = getattr(instance, field.source)
                    if not attachments.exists():
                        file_type = FileType.objects.get(
                            code=attachments.core_filters["code"]
                        )
                        Attachment.objects.create(
                            file_type=file_type,
                            file=None,
                            code=attachments.core_filters["code"],
                            content_object=instance
                        )
                fields[upload_field_name] = AttachmentUploadLinkField(
                    source=field.source
                )

    def save(self, *args, **kwargs):
        super(AttachmentSerializerMixin, self).save(*args, **kwargs)
        self.handle_upload_links()
        return self.instance
