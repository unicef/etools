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
    UserGroupForm,
)

from .models import (
    Agreement,
    # TODO intervention sector locations cleanup
    InterventionSectorLocationLink,
    PartnerOrganization,
    PartnerStaffMember,
)

logger = logging.getLogger('partners.forms')


# TODO intervention sector locations cleanup
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


class AgreementForm(UserGroupForm):

    ERROR_MESSAGES = {
        'end_date': 'End date must be greater than start date',
        'start_date_val': 'Start date must be greater than laatest of signed by partner/unicef date',
    }

    user_field = u'signed_by'
    group_name = u'Senior Management Team'

    def __init__(self, *args, **kwargs):
        super(AgreementForm, self).__init__(*args, **kwargs)
        if kwargs.get('instance', None) and kwargs["instance"].partner:
            self.fields['authorized_officers'].queryset = PartnerStaffMember.objects.filter(
                partner=kwargs["instance"].partner)
        else:
            self.fields['authorized_officers'].disabled = True
            self.fields['authorized_officers'].queryset = PartnerStaffMember.objects.none()

    class Meta:
        model = Agreement
        fields = '__all__'

    def clean(self):
        cleaned_data = super(AgreementForm, self).clean()

        partner = cleaned_data.get(u'partner')
        agreement_type = cleaned_data.get(u'agreement_type')
        # agreement_number = cleaned_data.get(u'agreement_number')
        start = cleaned_data.get(u'start')
        end = cleaned_data.get(u'end')
        signed_by_partner_date = cleaned_data.get(u'signed_by_partner_date')
        signed_by_unicef_date = cleaned_data.get(u'signed_by_unicef_date')

        if partner and agreement_type == Agreement.PCA:
            # Partner can only have one active PCA
            # pca_ids = partner.agreement_set.filter(agreement_type=Agreement.PCA).values_list('id', flat=True)
            # if (not self.instance.id and pca_ids) or \
            #         (self.instance.id and pca_ids and self.instance.id not in pca_ids):
            if start and end and \
                    partner.get_last_pca and \
                    partner.get_last_pca != self.instance:

                if start < partner.get_last_pca.end:
                    err = u'This partner can only have one active {} agreement'.format(agreement_type)
                    raise ValidationError({'agreement_type': err})

            #  set start date to one of the signed dates
            if start is None:
                # if both signed dates exist
                if signed_by_partner_date and signed_by_unicef_date:
                    if signed_by_partner_date > signed_by_unicef_date:
                        self.cleaned_data[u'start'] = signed_by_partner_date
                    else:
                        self.cleaned_data[u'start'] = signed_by_unicef_date

        if agreement_type == Agreement.PCA and partner.partner_type != u'Civil Society Organization':
            raise ValidationError(
                _(u'Only Civil Society Organizations can sign Programme Cooperation Agreements')
            )

        if agreement_type == Agreement.SSFA and start and end:
            if (end - start).days > 365:
                raise ValidationError(
                    _(u'SSFA can not be more than a year')
                )

        if start and end and start > end:
            raise ValidationError({'end': self.ERROR_MESSAGES['end_date']})

        # check if start date is greater than or equal than greatest signed date
        if signed_by_partner_date and signed_by_unicef_date and start:
            if signed_by_partner_date > signed_by_unicef_date:
                if start < signed_by_partner_date:
                    raise ValidationError({'start': self.ERROR_MESSAGES['start_date_val']})
            else:
                if start < signed_by_unicef_date:
                    raise ValidationError({'start': self.ERROR_MESSAGES['start_date_val']})

        if self.instance.id and self.instance.agreement_type != agreement_type \
                and signed_by_partner_date and signed_by_unicef_date:
            raise ValidationError(
                _(u'Agreement type can not be changed once signed by unicef and partner ')
            )

        # TODO: prevent more than one agreement being created for the current period
        # agreements = Agreement.objects.filter(
        #     partner=partner,
        #     start__lte=start,
        #     end__gte=end
        # )
        # if self.instance:
        #     agreements = agreements.exclude(id=self.instance.id)
        # if agreements:
        #     raise ValidationError(
        #         u'You can only have one current {} per partner'.format(
        #             agreement_type
        #         )
        #     )

        return cleaned_data
