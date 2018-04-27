
import logging

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.utils.translation import ugettext as _

from dal import autocomplete

from etools.applications.EquiTrack.forms import AutoSizeTextForm
from etools.applications.partners.models import \
    InterventionSectorLocationLink  # TODO intervention sector locations cleanup
from etools.applications.partners.models import PartnerOrganization, PartnerStaffMember, PartnerType

logger = logging.getLogger('partners.forms')


# TODO intervention sector locations cleanup
class SectorLocationForm(forms.ModelForm):
    class Meta:
        model = InterventionSectorLocationLink
        fields = ('sector', 'locations')
        widgets = {
            'locations': autocomplete.ModelSelect2Multiple(
                url='locations-autocomplete-light',
                attrs={
                    # Set some placeholder
                    'data-placeholder': 'Enter Location Name ...',
                    # Only trigger autocompletion after 3 characters have been typed
                    'data-minimum-input-length': 3,
                },
            )
        }


class PartnersAdminForm(AutoSizeTextForm):

    class Meta:
        model = PartnerOrganization
        fields = '__all__'

    def clean(self):
        cleaned_data = super(PartnersAdminForm, self).clean()

        partner_type = cleaned_data.get(u'partner_type')
        cso_type = cleaned_data.get(u'cso_type')

        if partner_type and partner_type == PartnerType.CIVIL_SOCIETY_ORGANIZATION and not cso_type:
            raise ValidationError(
                _(u'You must select a type for this CSO')
            )
        if partner_type and partner_type != PartnerType.CIVIL_SOCIETY_ORGANIZATION and cso_type:
            raise ValidationError(
                _(u'"CSO Type" does not apply to non-CSO organizations, please remove type')
            )
        return cleaned_data


class PartnerStaffMemberForm(forms.ModelForm):
    ERROR_MESSAGES = {
        'active_by_default': 'New Staff Member needs to be active at the moment of creation',
        'user_unavailable': 'The Partner Staff member you are trying to activate is associated with'
                            ' a different partnership'
    }

    def __init__(self, *args, **kwargs):
        super(PartnerStaffMemberForm, self).__init__(*args, **kwargs)

    class Meta:
        model = PartnerStaffMember
        fields = '__all__'

    def clean(self):
        cleaned_data = super(PartnerStaffMemberForm, self).clean()
        email = cleaned_data.get('email', "")
        active = cleaned_data.get('active')
        validate_email(email)
        User = get_user_model()

        partner_staff_members = []
        for u in User.objects.filter(Q(username=email) | Q(email=email)).all():
            if u.profile.partner_staff_member:
                partner_staff_members.append(u.profile.partner_staff_member)

        if not self.instance.pk:
            # user should be active first time it's created
            if not active:
                raise ValidationError({'active': self.ERROR_MESSAGES['active_by_default']})

            if partner_staff_members:
                raise ValidationError("This user already exists under a different partnership: {}".format(email))

        else:
            # make sure email addresses are not editable after creation.. user must be removed and re-added
            if email != self.instance.email:
                raise ValidationError(
                    "User emails cannot be changed, please remove the user and add another one: {}".format(email))

            # when adding the active tag to a previously untagged user
            if active and not self.instance.active:
                # make sure this user has not already been associated with another partnership.
                if [x for x in partner_staff_members if x != self.instance.pk]:
                    raise ValidationError({'active': self.ERROR_MESSAGES['user_unavailable']})

        return cleaned_data
