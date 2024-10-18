from datetime import date

from django.utils.translation import gettext as _, gettext_lazy

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin

from etools.applications.governments.models import GDDAmendment
from etools.applications.partners.serializers.interventions_v2 import PartnerStaffMemberUserSerializer
from etools.applications.users.serializers_v3 import MinimalUserSerializer


class GDDAmendmentCUSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    amendment_number = serializers.CharField(read_only=True)
    signed_amendment_attachment = AttachmentSingleFileField(read_only=True)
    internal_prc_review = AttachmentSingleFileField(required=False)
    unicef_signatory = MinimalUserSerializer(read_only=True)
    partner_authorized_officer_signatory = PartnerStaffMemberUserSerializer(read_only=True)

    class Meta:
        model = GDDAmendment
        fields = (
            'id',
            'amendment_number',
            'internal_prc_review',
            'created',
            'modified',
            'kind',
            'types',
            'other_description',
            'signed_date',
            'gdd',
            'amended_gdd',
            'is_active',
            # signatures
            'signed_by_unicef_date',
            'signed_by_partner_date',
            'unicef_signatory',
            'partner_authorized_officer_signatory',
            'signed_amendment_attachment',
            'difference',
            'created',
        )
        validators = [
            UniqueTogetherValidator(
                queryset=GDDAmendment.objects.filter(is_active=True),
                fields=["intervention", "kind"],
                message=gettext_lazy("Cannot add a new amendment while another amendment of same kind is in progress."),
            )
        ]
        extra_kwargs = {
            'is_active': {'read_only': True},
            'difference': {'read_only': True},
        }

    def validate_signed_by_unicef_date(self, value):
        if value and value > date.today():
            raise ValidationError(_("Date cannot be in the future!"))
        return value

    def validate_signed_by_partner_date(self, value):
        if value and value > date.today():
            raise ValidationError(_("Date cannot be in the future!"))
        return value

    def validate(self, data):
        data = super().validate(data)

        if 'intervention' in data:
            if data['intervention'].agreement.partner.blocked is True:
                raise ValidationError(_("Cannot add a new amendment while the partner is blocked in Vision."))

        if GDDAmendment.OTHER in data["types"]:
            if "other_description" not in data or not data["other_description"]:
                raise ValidationError(_("Other description required, if type 'Other' selected."))

        return data
