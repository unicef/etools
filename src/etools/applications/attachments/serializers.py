
from django.utils.translation import ugettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from etools.applications.attachments.models import Attachment, AttachmentFlat
from etools.applications.attachments.serializers_fields import Base64FileField
from etools.applications.users.serializers import SimpleUserSerializer
from etools.applications.utils.common.serializers.fields import SeparatedReadWriteField
from etools.applications.utils.common.serializers.mixins import UserContextSerializerMixin


class BaseAttachmentSerializer(UserContextSerializerMixin, serializers.ModelSerializer):
    uploaded_by = SeparatedReadWriteField(
        write_field=serializers.HiddenField(default=serializers.CurrentUserDefault()),
        read_field=SimpleUserSerializer(label=_('Uploaded By')),
    )

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
            'filename',
        ]
        extra_kwargs = {
            'created': {
                'label': _('Date Uploaded'),
            },
            'filename': {'read_only': True},
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
