
from django.utils.translation import ugettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from etools.applications.attachments.models import Attachment, AttachmentFlat
from etools.applications.attachments.serializers_fields import Base64FileField


class BaseAttachmentSerializer(serializers.ModelSerializer):
    def _validate_attachment(self, validated_data, instance=None):
        file_attachment = validated_data.get('file', None) or (instance.file if instance else None)
        hyperlink = validated_data.get('hyperlink', None) or (instance.hyperlink if instance else None)

        if bool(file_attachment) == bool(hyperlink):
            raise ValidationError(_('Please provide file or hyperlink.'))

    def create(self, validated_data):
        self._validate_attachment(validated_data)
        return super(BaseAttachmentSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        self._validate_attachment(validated_data, instance=instance)
        return super(BaseAttachmentSerializer, self).update(instance, validated_data)

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


class Base64AttachmentSerializer(BaseAttachmentSerializer):
    file = Base64FileField(required=False, label=_('File Attachment'))
    file_name = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        data = super(Base64AttachmentSerializer, self).validate(attrs)
        file_name = data.pop('file_name', None)
        if 'file' in data and file_name:
            data['file'].name = file_name
        return data

    class Meta(BaseAttachmentSerializer.Meta):
        fields = BaseAttachmentSerializer.Meta.fields + ['file_name', ]


class AttachmentFlatSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="attachment_id")

    class Meta:
        model = AttachmentFlat
        exclude = ("attachment", )


class AttachmentPDFSerializer(serializers.ModelSerializer):
    file_type_display = serializers.ReadOnlyField(source='file_type.label')
    created = serializers.DateTimeField(format='%d %b %Y')

    class Meta:
        model = Attachment
        fields = [
            'file_type_display', 'filename', 'url', 'created',
        ]
