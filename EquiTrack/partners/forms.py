from __future__ import absolute_import

import logging

from django.utils.translation import ugettext as _
from django import forms
from django.db.models import Q
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from dal import autocomplete

from EquiTrack.forms import (
    AutoSizeTextForm,
)

from .models import (
    InterventionSectorLocationLink,
    PartnerOrganization,
    PartnerStaffMember,
)

logger = logging.getLogger('partners.forms')


class SectorLocationForm(forms.ModelForm):
    class Meta:
        model = InterventionSectorLocationLink
        # fields = ('locations',)
        fields = ('sector', 'locations')
        # autocomplete_fields = ('locations',)
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
        cso_type = cleaned_data.get(u'type')

        if partner_type and partner_type == u'Civil Society Organisation' and not cso_type:
            raise ValidationError(
                _(u'You must select a type for this CSO')
            )
        if partner_type and partner_type != u'Civil Society Organisation' and cso_type:
            raise ValidationError(
                _(u'"CSO Type" does not apply to non-CSO organizations, please remove type')
            )
        return cleaned_data


class PartnerStaffMemberForm(forms.ModelForm):
    ERROR_MESSAGES = {
        'active_by_default': 'New Staff Member needs to be active at the moment of creation',
        'user_unavailable': 'The Partner Staff member you are trying to activate is associated with'
                            'a different partnership'
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
        existing_user = None
        if not self.instance.id:
            # user should be active first time it's created
            if not active:
                raise ValidationError({'active': self.ERROR_MESSAGES['active_by_default']})
            try:
                existing_user = User.objects.filter(Q(username=email) | Q(email=email)).get()
                if existing_user.profile.partner_staff_member:
                    raise ValidationError("This user already exists under a different partnership: {}".format(email))
            except User.DoesNotExist:
                pass

        else:
            # make sure email addresses are not editable after creation.. user must be removed and re-added
            if email != self.instance.email:
                raise ValidationError(
                    "User emails cannot be changed, please remove the user and add another one: {}".format(email))

            # when removing the active tag
            if self.instance.active and not active:
                pass

            # when adding the active tag to a previously untagged user
            if active and not self.instance.active:
                # make sure this user has not already been associated with another partnership.
                if existing_user:
                    if existing_user.partner_staff_member and \
                            existing_user.partner_staff_member != self.instance.pk:
                        raise ValidationError({'active': self.ERROR_MESSAGES['user_unavailable']})

        return cleaned_data
