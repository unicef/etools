from __future__ import absolute_import

__author__ = 'jcranwellward'

import pandas

from django.utils.translation import ugettext as _
from django import forms
from django.contrib import messages
#from autocomplete_light import forms
from django.core.exceptions import (
    ValidationError,
    ObjectDoesNotExist,
    MultipleObjectsReturned
)

from suit.widgets import AutosizedTextarea, LinkedSelect, SuitDateWidget

from EquiTrack.forms import (
    AutoSizeTextForm,
    ParentInlineAdminFormSet,
    RequireOneFormSet,
    UserGroupForm,
)
from locations.models import Location
from reports.models import Sector, Result, ResultType, Indicator
from .models import (
    PCA,
    PartnerOrganization,
    Assessment,
    GwPCALocation,
    ResultChain,
    AmendmentLog,
    Agreement,
    AuthorizedOfficer,
    PartnerStaffMember,
    SupplyItem,
    DistributionPlan,
    PartnershipBudget
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

        return cleaned_data


class AssessmentAdminForm(AutoSizeTextForm):

    class Meta:
        model = Assessment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        """
        Filter linked results by sector and result structure
        """
        if 'parent_object' in kwargs:
            self.parent_partnership = kwargs.pop('parent_object')

        super(AssessmentAdminForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(AssessmentAdminForm, self).clean()

        current = cleaned_data[u'current']

        if hasattr(self, 'parent_partnership'):
            exisiting = self.parent_partnership.assessments.filter(current=True).exclude(pk=self.instance.id)
            if exisiting and current:
                raise ValidationError(
                    _(u'You can only have assessment or audit as the basis of the risk rating')
                )

        return cleaned_data


class ResultChainAdminForm(forms.ModelForm):

    class Meta:
        model = ResultChain
        fields = '__all__'

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
            self.fields['result'].queryset = results

            if self.instance.result_id:
                self.fields['result'].queryset = results.filter(id=self.instance.result_id)


class AmendmentForm(forms.ModelForm):

    class Meta:
        model = AmendmentLog
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        """
        Only display the amendments related to this partnership
        """
        if 'parent_object' in kwargs:
            self.parent_partnership = kwargs.pop('parent_object')

        super(AmendmentForm, self).__init__(*args, **kwargs)

        self.fields['amendment'].queryset = self.parent_partnership.amendments_log \
            if hasattr(self, 'parent_partnership') else AmendmentLog.objects.none()

        self.fields['amendment'].empty_label = u'Original'


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
        fields = '__all__'

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
        fields = '__all__'

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
        fields = '__all__'
        widgets = {
            'start': SuitDateWidget,
            'end': SuitDateWidget,
        }

    def __init__(self, *args, **kwargs):
        super(AgreementForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(AgreementForm, self).clean()

        partner = cleaned_data[u'partner']
        agreement_type = cleaned_data[u'agreement_type']
        agreement_number = cleaned_data[u'agreement_number']

        if not agreement_number and agreement_type in [Agreement.PCA, Agreement.SSFA, Agreement.MOU]:
            raise ValidationError(
                _(u'Please provide the agreement reference for this {}'.format(agreement_type))
            )

        if agreement_type == Agreement.PCA and partner.partner_type != u'Civil Society Organisation':
            raise ValidationError(
                _(u'Only Civil Society Organisations can sign Programme Cooperation Agreements')
            )

        # TODO: prevent more than one agreement being crated for the current period
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


def check_and_return_value(column, row):

    value = 0
    if column in row:
        if not pandas.isnull(row[column]):
            value = row[column]
        row.pop(column)
    return value


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
        fields = '__all__'
        widgets = {
            'title': AutosizedTextarea(attrs={'class': 'input-xlarge'}),
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

        data.fillna('', inplace=True)
        current_output = None
        imported = found = not_found = 0
        for label, series in data.iterrows():
            create_args = dict(
                partnership=self.obj
            )
            row = series.to_dict()
            try:
                type = label.split()[0].strip()
                statement = row['Details'].strip()
                row.pop('Details')
                try:
                    result_type = ResultType.objects.get(
                        name__icontains=type
                    )
                except ResultType.DoesNotExist as exp:
                    # we can interpret the type we are dealing with by its label
                    if 'indicator' in label and current_output:
                        pass
                    else:
                        raise exp
                else:
                    # we are dealing with a result statement
                    # now we try to look up the result based on the statement
                    result, created = Result.objects.get_or_create(
                        result_structure=self.obj.result_structure,
                        result_type=result_type,
                        sector=sector,
                        name=statement,
                        code=label,
                    )
                    if result_type.name == 'Output':
                        current_output = result
                    elif result_type.name == 'Activity' and current_output:
                        result.parent = current_output
                        result.save()

                create_args['result'] = result
                create_args['result_type'] = result.result_type
                create_args['target'] = check_and_return_value('Targets', row)
                create_args['partner_contribution'] = check_and_return_value('CSO', row)
                create_args['unicef_cash'] = check_and_return_value('UNICEF Cash', row)
                create_args['in_kind_amount'] = check_and_return_value('UNICEF Supplies', row)
                check_and_return_value('Total', row)

                if 'indicator' in label:
                    indicator, created = Indicator.objects.get_or_create(
                        sector=sector,
                        result=result,
                        code=label,
                        name=statement
                    )
                    create_args['indicator'] = indicator

                result_chain, new = ResultChain.objects.get_or_create(**create_args)

                if row:
                    for key in row.keys():
                        if 'Unnamed' in key:
                            del row[key]
                        elif pandas.isnull(row[key]):
                            row[key] = ''
                    result_chain.disaggregation = row
                    result_chain.save()

                if new:
                    imported += 1
                else:
                    found += 1

            except (ObjectDoesNotExist, MultipleObjectsReturned) as exp:
                not_found += 1
                raise ValidationError(exp.message)

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
        start_date = cleaned_data[u'start_date']

        p_codes = cleaned_data[u'p_codes']
        location_sector = cleaned_data[u'location_sector']

        work_plan = self.cleaned_data[u'work_plan']
        work_plan_sector = self.cleaned_data[u'work_plan_sector']

        agreement_types = dict(Agreement.AGREEMENT_TYPES)
        partnership_types = dict(PCA.PARTNERSHIP_TYPES)
        agreement_types[PCA.PD] = agreement_types[Agreement.PCA]
        agreement_types[PCA.SHPD] = agreement_types[Agreement.PCA]

        if partnership_type:  #TODO: Remove check once partnership type is madatory

            if not agreement:
                raise ValidationError(
                    u'Please select the Agreement this Document relates to'
                )
            else:

                if agreement.agreement_type != partnership_type:
                    if agreement.agreement_type == Agreement.PCA and partnership_type in [PCA.PD, PCA.SHPD]:
                        pass  # This is acceptable as both PDs and SHPDs both relate to PCAs
                    else:
                        raise ValidationError(
                            u'Only {} can be selected for {}'.format(
                                agreement_types[partnership_type],
                                partnership_types[partnership_type]
                            )
                        )

                if partner_manager:
                    officers = agreement.authorized_officers.all().values_list('officer', flat=True)
                    if partner_manager.id not in officers:
                        raise ValidationError(
                            u'{} is not a named authorized officer in the {}'.format(
                                partner_manager, agreement
                            )
                        )

                if partnership_type not in [PCA.PD, PCA.SHPD]:
                    if not self.instance.pk and agreement.interventions.count():
                        raise ValidationError(
                                u'Only one intervention can be linked to this {}'.format(
                                    agreement
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

        if signed_by_unicef_date and start_date and (start_date < signed_by_unicef_date):
            raise ValidationError(
                u'The start date must be greater or equal to the singed by date'
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


class PartnershipBudgetAdminForm(AmendmentForm):

    class Meta:
        model = PartnershipBudget
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(PartnershipBudgetAdminForm, self).__init__(*args, **kwargs)

        years = None
        if hasattr(self, 'parent_partnership') and self.parent_partnership.start_date and self.parent_partnership.end_date:

            years = range(self.parent_partnership.start_date.year, self.parent_partnership.end_date.year+1)

        self.fields['year'] = forms.ChoiceField(
            choices=[(year, year) for year in years] if years else []
        )