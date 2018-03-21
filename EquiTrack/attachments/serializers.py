from __future__ import absolute_import, division, print_function, unicode_literals

from django.utils.translation import ugettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from attachments.models import Attachment
from attachments.serializers_fields import (
    Base64FileField
)
from partners.models import (
    Agreement,
    AgreementAmendment,
    Assessment,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    PartnerOrganization,
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


class AttachmentSerializer(BaseAttachmentsSerializer):
    created = serializers.DateTimeField(format='%d %b %Y')
    file_type = serializers.SerializerMethodField(source='file_type.label')
    file_link = serializers.CharField()
    filename = serializers.CharField()
    partner = serializers.SerializerMethodField()
    partner_type = serializers.SerializerMethodField()
    vendor_number = serializers.SerializerMethodField()
    pd_ssfa_number = serializers.SerializerMethodField()

    class Meta(BaseAttachmentsSerializer.Meta):
        fields = [
            'id',
            'partner',
            'vendor_number',
            'partner_type',
            'pd_ssfa_number',
            'created',
            'file_type',
            'file_link',
            'filename',
            'uploaded_by'
        ]

    def get_file_type(self, obj):
        """If dealing with intervention attachment then use
        partner file type instead of attachement file type
        """
        if isinstance(obj.content_object, InterventionAttachment):
            return obj.content_object.type.name
        return obj.file_type.label

    def get_partner_obj(self, obj):
        """Try and get partner value"""
        if isinstance(obj.content_object, PartnerOrganization):
            return obj.content_object
        elif isinstance(obj.content_object, (AgreementAmendment, Intervention)):
            return obj.content_object.agreement.partner
        elif isinstance(obj.content_object, (InterventionAmendment, InterventionAttachment)):
            return obj.content_object.intervention.agreement.partner
        elif isinstance(obj.content_object, (Agreement, Assessment)):
            return obj.content_object.partner
        return None

    def get_partner(self, obj):
        partner = self.get_partner_obj(obj)
        if partner is not None:
            return partner.name
        return None

    def get_vendor_number(self, obj):
        """Try and get partner value, from there get vendor number"""
        partner = self.get_partner_obj(obj)
        if partner is not None:
            return partner.vendor_number
        return None

    def get_partner_type(self, obj):
        partner = self.get_partner_obj(obj)
        if partner is not None:
            return partner.partner_type
        return None

    def get_pd_ssfa_number(self, obj):
        """Only certain models will have this value available
        Intervention
        InterventionAttachment
        InterventionAmendment
        """
        if isinstance(obj.content_object, Intervention):
            return obj.content_object.number
        elif isinstance(obj.content_object, (InterventionAmendment, InterventionAttachment)):
            return obj.content_object.intervention.number
        return None
