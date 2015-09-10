from __future__ import absolute_import

__author__ = 'jcranwellward'

#import pandas



from django.utils.translation import ugettext as _
from django import forms
from django.contrib import messages
#from autocomplete_light import forms
from django.core.exceptions import (
    ValidationError,
    ObjectDoesNotExist,
    MultipleObjectsReturned
)

from suit.widgets import AutosizedTextarea, LinkedSelect

from EquiTrack.forms import (
    ParentInlineAdminFormSet,
    RequireOneFormSet,
    UserGroupForm,
)
from locations.models import Location
from reports.models import Sector, Result, Indicator
from .models import (
    PCA,
    GwPCALocation,
    ResultChain,
    IndicatorProgress,
    AmendmentLog,
    Agreement,
    AuthorizedOfficer,
    PartnerStaffMember,
    SupplyItem,
    DistributionPlan,
)


# class LocationForm(forms.ModelForm):
#
#     class Media:
#         """
#         We're currently using Media here, but that forced to move the
#         javascript from the footer to the extrahead block ...
#
#         So that example might change when this situation annoys someone a lot.
#         """
#         js = ('dependant_autocomplete.js',)
#
#     class Meta:
#         model = GwPCALocation


class IndicatorAdminModelForm(forms.ModelForm):

    class Meta:
        model = IndicatorProgress

    def __init__(self, *args, **kwargs):
        super(IndicatorAdminModelForm, self).__init__(*args, **kwargs)
        self.fields['indicator'].queryset = []


class ResultChainAdminForm(forms.ModelForm):

    class Meta:
        model = ResultChain

    def __init__(self, *args, **kwargs):
        """
        Filter linked results by sector and result structure
        """
        if 'parent_object' in kwargs:
            self.parent_partnership = kwargs.pop('parent_object')

        super(ResultChainAdminForm, self).__init__(*args, **kwargs)

        if hasattr(self, 'parent_partnership'):

            results = Result.objects.filter(
                result_structure=self.parent_partnership.result_structure
            )
            indicators = Indicator.objects.filter(
                result_structure=self.parent_partnership.result_structure
            )
            for sector in self.parent_partnership.sector_children:
                results = results.filter(sector=sector)
                indicators = indicators.filter(sector=sector)

            if self.instance.result_id:
                self.fields['result'].queryset = results.filter(id=self.instance.result_id)
                self.fields['indicator'].queryset = indicators.filter(result_id=self.instance.result_id)


class AmendmentForm(forms.ModelForm):

    class Meta:
        model = AmendmentLog

    def __init__(self, *args, **kwargs):
        """
        Only display the amendments related to this partnership
        """
        if 'parent_object' in kwargs:
            self.parent_partnership = kwargs.pop('parent_object')

        super(AmendmentForm, self).__init__(*args, **kwargs)

        self.fields['amendment'].queryset = self.parent_partnership.amendments_log \
            if hasattr(self, 'parent_partnership') else AmendmentLog.objects.none()


class AuthorizedOfficesFormset(RequireOneFormSet):

    def __init__(
            self, data=None, files=None, instance=None,
            save_as_new=False, prefix=None, queryset=None, **kwargs):
        super(AuthorizedOfficesFormset, self).__init__(
            data=data, files=files, instance=instance,
            save_as_new=save_as_new, prefix=prefix,
            queryset=queryset, **kwargs)
        self.required = False

    def _construct_form(self, i, **kwargs):
        form = super(AuthorizedOfficesFormset, self)._construct_form(i, **kwargs)
        if self.instance.signed_by_partner_date:
            self.required = True
        return form


class AuthorizedOfficersForm(forms.ModelForm):

    class Meta:
        model = AuthorizedOfficer
        widgets = {
            'officer': LinkedSelect,
        }

    def __init__(self, *args, **kwargs):
        """
        Only display the officers of the partner related to the agreement
        """
        if 'parent_object' in kwargs:
            self.parent_agreement = kwargs.pop('parent_object')

        super(AuthorizedOfficersForm, self).__init__(*args, **kwargs)

        self.fields['officer'].queryset = PartnerStaffMember.objects.filter(
            partner=self.parent_agreement.partner
        ) if hasattr(self, 'parent_agreement') \
             and hasattr(self.parent_agreement, 'partner') else PartnerStaffMember.objects.none()


class DistributionPlanForm(forms.ModelForm):

    class Meta:
        model = DistributionPlan

    def __init__(self, *args, **kwargs):
        """
        Only show supply items already in the supply plan
        """
        if 'parent_object' in kwargs:
            self.parent_partnership = kwargs.pop('parent_object')

        super(DistributionPlanForm, self).__init__(*args, **kwargs)

        queryset = SupplyItem.objects.none()
        if hasattr(self, 'parent_partnership'):

            items = self.parent_partnership.supply_plans.all().values_list('item__id', flat=True)
            queryset = SupplyItem.objects.filter(id__in=items)

        self.fields['item'].queryset = queryset


class DistributionPlanFormSet(ParentInlineAdminFormSet):

    def clean(self):
        """
        Ensure distribution plans are inline with overall supply plan
        """
        cleaned_data = super(DistributionPlanFormSet, self).clean()

        if self.instance:
            for plan in self.instance.supply_plans.all():
                total_quantity = 0
                for form in self.forms:
                    if form.cleaned_data.get('DELETE', False):
                        continue
                    data = form.cleaned_data
                    if plan.item == data.get('item', 0):
                        total_quantity += data.get('quantity', 0)

                if total_quantity > plan.quantity:
                    raise ValidationError(
                        _(u'The total quantity ({}) of {} exceeds the planned amount of {}'.format(
                            total_quantity, plan.item, plan.quantity))
                    )

        return cleaned_data


class AgreementForm(UserGroupForm):

    user_field = u'signed_by'
    group_name = u'Senior Management Team'

    class Meta:
        model = Agreement
        widgets = {
            'partner': LinkedSelect,
            'signed_by': LinkedSelect,
            'partner_manager': LinkedSelect,
        }

    def __init__(self, *args, **kwargs):
        super(AgreementForm, self).__init__(*args, **kwargs)
        self.fields['start'].required = True
        self.fields['end'].required = True

    def clean(self):
        cleaned_data = super(AgreementForm, self).clean()

        partner = cleaned_data[u'partner']
        agreement_type = cleaned_data[u'agreement_type']
        start = cleaned_data[u'start']
        end = cleaned_data[u'end']

        # prevent more than one agreement being crated for the current period
        agreements = Agreement.objects.filter(
            partner=partner,
            start__lte=start,
            end__gte=end
        )
        if self.instance:
            agreements = agreements.exclude(id=self.instance.id)
        if agreements:
            raise ValidationError(
                u'You can only have one current {} per partner'.format(
                    agreement_type
                )
            )

        return cleaned_data


class PartnershipForm(UserGroupForm):

    user_field = u'unicef_manager'
    group_name = u'Senior Management Team'

    # fields needed to assign locations from p_codes
    p_codes = forms.CharField(widget=forms.Textarea, required=False)
    location_sector = forms.ModelChoiceField(
        required=False,
        queryset=Sector.objects.all()
    )

    # fields needed to import log frames/work plans from excel
    work_plan = forms.FileField(required=False)
    work_plan_sector = forms.ModelChoiceField(
        required=False,
        queryset=Sector.objects.all()
    )

    class Meta:
        model = PCA
        widgets = {
            'title': AutosizedTextarea(attrs={'class': 'input-xlarge'}),
            'agreement': LinkedSelect,
        }

    def add_locations(self, p_codes, sector):
        """
        Adds locations to the partnership based
        on the passed in list and the relevant sector
        """
        p_codes_list = p_codes.split()
        created, notfound = 0, 0
        for p_code in p_codes_list:
            try:
                location = Location.objects.get(
                    p_code=p_code
                )
                loc, new = GwPCALocation.objects.get_or_create(
                    sector=sector,
                    governorate=location.locality.region.governorate,
                    region=location.locality.region,
                    locality=location.locality,
                    location=location,
                    pca=self.obj
                )
                if new:
                    created += 1
            except Location.DoesNotExist:
                notfound += 1

        messages.info(
            self.request,
            u'Assigned {} locations, {} were not found'.format(
                created, notfound
            ))

    def import_results_from_work_plan(self, work_plan, sector):
        """
        Matches results from the work plan to country result structure.
        Will try to match indicators one to one or by name, this can be ran
        multiple times to continually update the work plan
        """
        try:  # first try to grab the excel as a table...
            data = pandas.read_excel(work_plan, index_col=0)
        except Exception as exp:
            raise ValidationError(exp.message)

        imported = found = not_found = 0
        for code, row in data.iterrows():
            create_args = dict(
                partnership=self.obj
            )
            try:
                result = Result.objects.get(
                    sector=sector,
                    code=code
                )
                create_args['result'] = result
                create_args['result_type'] = result.result_type
                indicators = result.indicator_set.all()
                if indicators:
                    if indicators.count() == 1:
                        # use this indicator if we only have one
                        create_args['indicator'] = indicators[0]
                    else:
                        # attempt to fuzzy match by name
                        candidates = indicators.filter(
                            name__icontains=row['Indicator']
                        )
                        if candidates:
                            create_args['indicator'] = candidates[0]
                    # if we got this far also take the target
                    create_args['target'] = row.get('Target')
            except (ObjectDoesNotExist, MultipleObjectsReturned) as exp:
                not_found += 1
                #TODO: Log this
            else:
                result_chain, new = ResultChain.objects.get_or_create(**create_args)
                if new:
                    imported += 1
                else:
                    found += 1

        messages.info(
            self.request,
            u'Imported {} results, {} were imported already and {} were not found'.format(
                imported, found, not_found
            ))

    def clean(self):
        """
        Add elements to the partnership based on imports
        """
        cleaned_data = super(PartnershipForm, self).clean()

        partnership_type = cleaned_data[u'partnership_type']
        agreement = cleaned_data[u'agreement']
        unicef_manager = cleaned_data[u'unicef_manager']
        signed_by_unicef_date = cleaned_data[u'signed_by_unicef_date']
        partner_manager = cleaned_data[u'partner_manager']
        signed_by_partner_date = cleaned_data[u'signed_by_partner_date']

        p_codes =cleaned_data[u'p_codes']
        location_sector = cleaned_data[u'location_sector']

        work_plan = self.cleaned_data[u'work_plan']
        work_plan_sector = self.cleaned_data[u'work_plan_sector']

        if partnership_type == PCA.PD:

            if not agreement:
                raise ValidationError(
                    u'Please select the PCA agreement this Programme Document relates to'
                )

            if partner_manager:
                officers = agreement.authorized_officers.all().values_list('officer', flat=True)
                if partner_manager.id not in officers:
                    raise ValidationError(
                        u'{} is not a named authorized officer in the {}'.format(
                            partner_manager, agreement
                        )
                    )

        if unicef_manager and not signed_by_unicef_date:
            raise ValidationError(
                u'Please select the date {} signed the partnership'.format(unicef_manager)
            )

        if partner_manager and not signed_by_partner_date:
            raise ValidationError(
                u'Please select the date {} signed the partnership'.format(partner_manager)
            )

        if p_codes and not location_sector:
            raise ValidationError(
                u'Please select a sector to assign the locations against'
            )

        if p_codes and location_sector:
            self.add_locations(p_codes, location_sector)

        if work_plan and not work_plan_sector:
            raise ValidationError(
                u'Please select a sector to import results against'
            )

        if work_plan and work_plan_sector:
            self.import_results_from_work_plan(work_plan, work_plan_sector)

        return cleaned_data
