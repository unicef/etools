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
        fields = ['id', 'file_type', 'file', 'hyperlink', 'created', 'modified', ]
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
    file_type = serializers.CharField(source='file_type.name')
    url = serializers.SerializerMethodField()
    filename = serializers.CharField()

    class Meta(BaseAttachmentsSerializer.Meta):
        fields = [
            'created', 'file_type', 'url', 'filename',
        ]

    def get_url(self, obj):
        return urllib_parse.urljoin(site_url(), obj.url)


class AttachmentFileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ["file", ]


class AttachmentSerializerMixin(object):
    def save(self, **kwargs):
        super(AttachmentSerializerMixin, self).save(**kwargs)

        # check if attachment field types exist
        # if exists and field has value
        # ensure attachment record exists for instance
        # set upload link value
        for field_name, field in self.fields.items():
            if isinstance(field, AttachmentSingleFileField):
                attachments = getattr(self.instance, field.source)
                if not attachments.exists():
                    file_type = FileType.objects.get(
                        code=attachments.core_filters["code"]
                    )
                    Attachment.objects.create(
                        file_type=file_type,
                        file=None,
                        code=attachments.core_filters["code"],
                        content_object=self.instance
                    )
                upload_field_name = "{}_upload_link".format(field_name)
                self.fields[upload_field_name] = AttachmentUploadLinkField(
                    source=field.source
                )

        return self.instance
