from __future__ import absolute_import

__author__ = 'jcranwellward'

import pandas
import logging
from datetime import date

from django.utils.translation import ugettext as _
from django import forms
from django.contrib import messages
from django.db.models import Q
from django.db import connection
from django.core.validators import validate_email

from autocomplete_light import forms as auto_forms
from django.core.exceptions import (
    ValidationError,
    ObjectDoesNotExist,
    MultipleObjectsReturned
)

from suit.widgets import AutosizedTextarea, SuitDateWidget

from EquiTrack.forms import (
    AutoSizeTextForm,
    ParentInlineAdminFormSet,
    UserGroupForm,
)

from django.contrib.auth.models import User

from reports.models import (
    ResultStructure,
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
    AgreementAmendmentLog,
    Agreement,
    AuthorizedOfficer,
    PartnerStaffMember,
    SupplyItem,
    DistributionPlan,
    PartnershipBudget,
    GovernmentIntervention,
)

logger = logging.getLogger('partners.forms')


class LocationForm(auto_forms.ModelForm):

    class Meta:
        model = GwPCALocation
        fields = ('location',)
        autocomplete_fields = ('location',)


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


class GovernmentInterventionAdminForm(forms.ModelForm):

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(GovernmentInterventionAdminForm, self).__init__(*args, **kwargs)

        # by default add the previous 1 years and the next 2 years
        current_year = date.today().year
        years = range(current_year - 1, current_year + 2)

        self.fields['year'] = forms.ChoiceField(
            choices=[(year, year) for year in years]
        )
        self.fields['year'].empty_label = u'Select year'


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


class AgreementAmendmentForm(AmendmentForm):

    class Meta:
        model = AgreementAmendmentLog
        fields = '__all__'


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
                raise ValidationError("User emails cannot be changed, please remove the user and add another one: {}".format(email))

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

        self.fields['amendment'].queryset = self.parent_agreement.amendments_log \
            if hasattr(self, 'parent_agreement') else AgreementAmendmentLog.objects.none()
        self.fields['amendment'].empty_label = u'Original'


class DistributionPlanForm(auto_forms.ModelForm):

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

    def clean(self):
        cleaned_data = super(AgreementForm, self).clean()

        partner = cleaned_data.get(u'partner')
        agreement_type = cleaned_data.get(u'agreement_type')
        agreement_number = cleaned_data.get(u'agreement_number')
        start = cleaned_data.get(u'start')
        end = cleaned_data.get(u'end')
        signed_by_partner_date = cleaned_data.get(u'signed_by_partner_date')
        signed_by_unicef_date = cleaned_data.get(u'signed_by_unicef_date')


        if partner and agreement_type == Agreement.PCA:
            # Partner can only have one active PCA
            # pca_ids = partner.agreement_set.filter(agreement_type=Agreement.PCA).values_list('id', flat=True)
            # if (not self.instance.id and pca_ids) or \
            #         (self.instance.id and pca_ids and self.instance.id not in pca_ids):
            if partner.get_last_agreement and partner.get_last_agreement != self.instance:
                if not start > partner.get_last_agreement.start and not end > partner.get_last_agreement.end:
                    err = u'This partner can only have one active {} agreement'.format(agreement_type)
                    raise ValidationError({'agreement_type': err})

            # PCAs last as long as the most recent CPD
            result_structure = ResultStructure.current()
            if result_structure and end and end > result_structure.to_date:
                raise ValidationError(
                    {'end': u'This agreement cannot last longer than the current {} which ends on {}'.format(
                        result_structure.name, result_structure.to_date
                    )}
                )

        if agreement_type == Agreement.PCA and partner.partner_type != u'Civil Society Organization':
            raise ValidationError(
                _(u'Only Civil Society Organizations can sign Programme Cooperation Agreements')
            )

        if agreement_type == Agreement.SSFA and start and end:
            if (end - start).days > 365:
                raise ValidationError(
                    _(u'SSFA can not be more than a year')
                )

        #  set start date to one of the signed dates
        if start is None and agreement_type == Agreement.PCA:
            # if both signed dates exist
            if signed_by_partner_date and signed_by_unicef_date:
                if signed_by_partner_date > signed_by_unicef_date:
                    self.cleaned_data[u'start'] = signed_by_partner_date
                else:
                    self.cleaned_data[u'start'] = signed_by_unicef_date

        # set end date to result structure end date
        if end is None:
            self.cleaned_data[u'end'] = ResultStructure.current().to_date

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


def check_and_return_value(column, row, row_num, number=False):

    value = 0
    if column in row:
        if not pandas.isnull(row[column]) and row[column]:
            # In case numbers are written in locale eg: u"6,000"
            if number and type(row[column]) in [str, unicode]:
                try:
                    value = int(row[column].replace(',', ''))
                except ValueError:
                    raise ValidationError(u"The value {} received for row {} column {} is not numeric."
                                          .format(row[column], row_num, column))
            elif 0.01 <= row[column] <= 0.99:
                value = int(row[column] * 100)
            else:
                value = row[column]
        row.pop(column)
    return value


def parse_disaggregate_val(csvs):
    return [x.strip() for x in csvs.split(',')]


class PartnershipForm(UserGroupForm):
    ERROR_MESSAGES = {
        'signed_by_partner': 'Signed by partner date must be later than submission date and submission date to PRC',
        'partner_manager': 'Please select a partner manager for the signed date',
        'submission_date': 'Submition date to PRC must be later than submission date',
        'review_date': 'Review date by PRC must be later than submission date and submission date to PRC'
    }

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

    def import_results_from_work_plan(self, work_plan):
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
        result_structure = self.obj.result_structure or ResultStructure.current()
        imported = found = not_found = row_num = 0
        # TODO: make sure to check all the expected columns are in

        for label, series in data.iterrows():
            create_args = dict(
                partnership=self.obj
            )
            row_num += 1
            row = series.to_dict()
            labels = list(series.axes[0])  # get the labels in order

            # check if there are correct time frames set on activities:
            at_least_one_tf = [x for x in labels if 'TF_' in x]
            if not at_least_one_tf:
                raise ValidationError('There are no valid time frames for the activities,'
                                      'please prefix activities with "TF_')

            try:
                type = label.split()[0].strip()
                statement = row.pop('Details').strip()
                try:
                    result_type = ResultType.objects.get(
                        name__icontains=type
                    )
                except ResultType.DoesNotExist as exp:
                    # we can interpret the type we are dealing with by its label
                    if 'indicator' not in type and current_output:
                        raise ValidationError(
                            _(u"The value of the first column must be one of: Output, Indicator or Activity."
                              u"The value received for row {} was: {}".format(row_num, type)))
                else:
                    # we are dealing with a result statement
                    # now we try to look up the result based on the statement
                    result, created = Result.objects.get_or_create(
                        result_structure=result_structure,
                        result_type=result_type,
                        name=statement,
                        code=label,
                        hidden=True,
                    )
                    if result_type.name == 'Output':
                        current_output = result
                    elif result_type.name == 'Activity' and current_output:
                        result.parent = current_output
                        result.save()

                create_args['result'] = result
                create_args['result_type'] = result.result_type
                create_args['partner_contribution'] = check_and_return_value('CSO', row, row_num, number=True)
                create_args['unicef_cash'] = check_and_return_value('UNICEF Cash', row, row_num, number=True)
                create_args['in_kind_amount'] = check_and_return_value('UNICEF Supplies', row, row_num, number=True)
                target = check_and_return_value('Targets', row, row_num, number=True)
                check_and_return_value('Total', row, row_num, number=True)  # ignore value as we calculate this

                if 'indicator' in label:
                    indicator, created = Indicator.objects.get_or_create(
                        result=result,
                        code=label,
                        name=statement
                    )
                    create_args['indicator'] = indicator
                    create_args['target'] = target

                    for key in row.keys():
                        # "TP_" refers to activity time periods
                        if 'Unnamed' in key or \
                                'TF_' in key or \
                                pandas.isnull(row[key]) or \
                                not row[key]:
                            del row[key]
                            continue
                        row[key] = parse_disaggregate_val(row[key])

                    create_args['disaggregation'] = None
                    if row:
                        order = [e for e in labels if row.get(e)]
                        row['order'] = order
                        create_args['disaggregation'] = row.copy()
                else:
                    # this is an activity
                    for key in row.keys():
                        if 'Unnamed' in key or 'TF_' not in key:
                            del row[key]
                        elif pandas.isnull(row[key]):
                            row[key] = ''

                    create_args['disaggregation'] = row.copy() if row else None

                result_chain, new = ResultChain.objects.get_or_create(**create_args)

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
        result_structure = cleaned_data.get(u'result_structure')
        agreement = cleaned_data[u'agreement']
        unicef_manager = cleaned_data[u'unicef_manager']
        signed_by_unicef_date = cleaned_data[u'signed_by_unicef_date']
        partner_manager = cleaned_data[u'partner_manager']
        signed_by_partner_date = cleaned_data[u'signed_by_partner_date']
        start_date = cleaned_data[u'start_date']
        end_date = cleaned_data[u'end_date']
        initiation_date = cleaned_data[u'initiation_date']
        submission_date = cleaned_data[u'submission_date']
        review_date = cleaned_data[u'review_date']


        p_codes = cleaned_data[u'p_codes']
        location_sector = cleaned_data[u'location_sector']

        work_plan = self.cleaned_data[u'work_plan']

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

        if signed_by_partner_date and signed_by_partner_date < initiation_date:
            raise ValidationError({'signed_by_partner_date': self.ERROR_MESSAGES['signed_by_partner']})

        if signed_by_partner_date and not partner_manager:
            raise ValidationError({'partner_manager': self.ERROR_MESSAGES['partner_manager']})

        if signed_by_unicef_date and not unicef_manager:
            raise ValidationError(
                u'Please select a unicef manager for the signed date'
            )

        if signed_by_unicef_date and start_date and (start_date < signed_by_unicef_date):
            raise ValidationError(
                u'The start date must be greater or equal to the singed by date'
            )

        if p_codes and not location_sector:
            raise ValidationError(
                u'Please select a sector to assign the locations against'
            )

        if start_date and agreement.start and start_date < agreement.start:
            err = u'The Intervention must start after the agreement starts on: {}'.format(
                agreement.start
            )
            raise ValidationError({'start_date': err})

        if start_date and end_date and start_date > end_date:
            err = u'The end date has to be after the start date'
            raise ValidationError({'end_date': err})

        if submission_date and submission_date < initiation_date:
            raise ValidationError({'submission_date': self.ERROR_MESSAGES['submission_date']})

        if review_date and review_date < submission_date and review_date < initiation_date:
            raise ValidationError({'review_date': self.ERROR_MESSAGES['review_date']})

        if p_codes and location_sector:
            self.add_locations(p_codes, location_sector)

        if work_plan:
            # make sure the status of the intervention is in process
            if self.instance.status != PCA.IN_PROCESS:
                raise ValidationError(
                    u'After the intervention is signed, the workplan cannot be changed'
                )
            if result_structure is None:
                raise ValidationError(
                    u'Please select a result structure from the man info tab to import results against'
                )
            # make sure another workplan has not been uploaded already:
            if self.instance.results and self.instance.results.count() > 0:
                self.instance.results.all().delete()
            self.import_results_from_work_plan(work_plan)

        return cleaned_data


class PartnershipBudgetAdminForm(AmendmentForm):

    class Meta:
        model = PartnershipBudget
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(PartnershipBudgetAdminForm, self).__init__(*args, **kwargs)

        # by default add the previous 1 years and the next 2 years
        current_year = date.today().year
        years = range(current_year-1, current_year+2)
        if (hasattr(self, 'parent_partnership')) and \
                self.parent_partnership.start_date and \
                self.parent_partnership.end_date:
            years = range(self.parent_partnership.start_date.year,
                          self.parent_partnership.end_date.year+1)

        self.fields['year'] = forms.ChoiceField(
            choices=[(year, year) for year in years] if years else []
        )
