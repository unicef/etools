import logging

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connection
from django.db.models import Q
from django.utils.translation import gettext as _

from unicef_djangolib.forms import AutoSizeTextForm

from etools.applications.partners.models import (
    Intervention,
    InterventionAttachment,
    PartnerOrganization,
    PartnerStaffMember,
    PartnerType,
)

logger = logging.getLogger('partners.forms')


class PartnersAdminForm(AutoSizeTextForm):

    class Meta:
        model = PartnerOrganization
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()

        partner_type = cleaned_data.get('partner_type')
        cso_type = cleaned_data.get('cso_type')

        if partner_type and partner_type == PartnerType.CIVIL_SOCIETY_ORGANIZATION and not cso_type:
            raise ValidationError(
                _('You must select a type for this CSO')
            )
        if partner_type and partner_type != PartnerType.CIVIL_SOCIETY_ORGANIZATION and cso_type:
            raise ValidationError(
                _('"CSO Type" does not apply to non-CSO organizations, please remove type')
            )
        return cleaned_data


class PartnerStaffMemberForm(forms.ModelForm):
    ERROR_MESSAGES = {
        'active_by_default': 'New Staff Member needs to be active at the moment of creation',
        'user_unavailable': 'The Partner Staff member you are trying to activate is associated with'
                            ' a different partnership',
        "user_mismatch": "User Mismatch",
        "psm_mismatch": "User is associated with another staff member record in {}"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = PartnerStaffMember
        exclude = ("user", )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email', "")
        active = cleaned_data.get('active')
        validate_email(email)
        User = get_user_model()

        if not self.instance.pk:
            # user should be active first time it's created
            if not active:
                raise ValidationError({'active': self.ERROR_MESSAGES['active_by_default']})

            user = User.objects.filter(email__iexact=email).first()
            if user:
                if user.is_unicef_user():
                    raise ValidationError(_('Unable to associate staff member to UNICEF user'))

                staff_member = user.get_partner_staff_member()
                if staff_member:
                    raise ValidationError(
                        _("This user already exists under a different partnership: %s") % email)

                cleaned_data['user'] = user
        else:
            # make sure email addresses are not editable after creation.. user must be removed and re-added
            if email != self.instance.email:
                raise ValidationError(
                    _("User emails cannot be changed, please remove the user and add another one: %s") % email)

            # when adding the active tag to a previously untagged user
            if active and not self.instance.active:
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    pass
                else:
                    if self.instance.user != user:
                        raise ValidationError({'email': self.ERROR_MESSAGES['user_mismatch']})

                    psm_country = user.get_staff_member_country()
                    if psm_country and psm_country != connection.tenant:
                        raise ValidationError({'email': self.ERROR_MESSAGES['psm_mismatch'].
                                              format(psm_country)})

            # disabled is unavailable if user already synced to PRP to avoid data inconsistencies
            if self.instance.active and not active:
                if Intervention.objects.filter(
                    Q(date_sent_to_partner__isnull=False, agreement__partner__staff_members=self.instance) |
                    Q(
                        ~Q(status=Intervention.DRAFT),
                        Q(partner_focal_points=self.instance) | Q(partner_authorized_officer_signatory=self.instance),
                    ),
                ).exists():
                    raise ValidationError({'active': _('User already synced to PRP and cannot be disabled.')})

        return cleaned_data

    def save(self, commit=True):
        User = get_user_model()

        if not self.instance.pk:
            if 'user' in self.cleaned_data:
                self.instance.user = self.cleaned_data['user']
            else:
                self.instance.user = User.objects.create(
                    first_name=self.instance.first_name,
                    last_name=self.instance.last_name,
                    email=self.instance.email,
                    username=self.instance.email,
                    is_active=True,
                    is_staff=False,
                )

        return super().save(commit=commit)


class InterventionAttachmentForm(forms.ModelForm):
    class Meta:
        model = InterventionAttachment
        fields = (
            'type',
            'attachment',
        )

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance", None)
        if instance:
            attachment = instance.attachment_file.last()
            if attachment:
                instance.attachment = attachment.file
        super().__init__(*args, **kwargs)
