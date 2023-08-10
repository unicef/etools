import logging
from datetime import date

from django.utils.translation import gettext as _

from etools_validator.exceptions import (
    BasicValidationError,
    DetailedStateValidationError,
    StateValidationError,
    TransitionError,
)
from etools_validator.utils import check_required_fields, check_rigid_fields
from etools_validator.validation import CompleteValidation

from etools.applications.partners.permissions import InterventionPermissions
from etools.applications.reports.models import AppliedIndicator, InterventionActivity

logger = logging.getLogger('partners.interventions.validation')


def partnership_manager_only(i, user):
    # Transition cannot happen by a user that's not a Partnership Manager
    if not user.groups.filter(name__in=['Partnership Manager']).count():
        raise TransitionError([_('Only Partnership Managers can execute this transition')])
    return True


def transition_ok(i):
    return True


def transition_to_closed(i):
    from etools.applications.partners.models import InterventionAmendment

    # unicef/etools-issues:820
    # TODO: this is required to go around the caching of intervention.total_frs where self.frs.all() is called
    # TODO: find a sol for invalidating the cache on related .all() -has to do with prefetch_related in the validator
    r = {
        'total_frs_amt': 0,
        'total_frs_amt_usd': 0,
        'total_outstanding_amt': 0,
        'total_outstanding_amt_usd': 0,
        'total_intervention_amt': 0,
        'total_actual_amt': 0,
        'total_actual_amt_usd': 0,
        'earliest_start_date': None,
        'latest_end_date': None,
        'total_completed_flag': True
    }
    for fr in i.frs.filter():
        # either they're all marked as completed or it's False
        r['total_completed_flag'] = fr.completed_flag and r['total_completed_flag']
        r['total_frs_amt'] += fr.total_amt_local
        r['total_frs_amt_usd'] += fr.total_amt
        r['total_outstanding_amt'] += fr.outstanding_amt_local
        r['total_outstanding_amt_usd'] += fr.outstanding_amt
        r['total_intervention_amt'] += fr.intervention_amt
        r['total_actual_amt'] += fr.actual_amt_local
        r['total_actual_amt_usd'] += fr.actual_amt
        if r['earliest_start_date'] is None:
            r['earliest_start_date'] = fr.start_date
        elif r['earliest_start_date'] > fr.start_date:
            r['earliest_start_date'] = fr.start_date
        if r['latest_end_date'] is None:
            r['latest_end_date'] = fr.end_date
        elif r['latest_end_date'] < fr.end_date:
            r['latest_end_date'] = fr.end_date
    # hack
    i.total_frs = r

    # Make sure that is past the end date
    today = date.today()
    if i.end > today:
        raise TransitionError([_('End date is in the future')])

    # In case FRs are marked as completed validation needs to move forward regardless of value discrepancy
    # In case it's a supply only PD, the total FRs will be $0.01 and validation needs to move forward
    # to be safe given decimal field here compare to a float we're saying smaller than $0.1 & continue with validation
    if i.total_frs['total_completed_flag']:
        if i.total_frs['total_outstanding_amt'] != 0:
            raise TransitionError(
                [_('Total Outstanding DCTs need to equal to 0')],
            )
    else:
        if not float(i.total_frs['total_frs_amt']) < 0.1:
            if (
                    i.total_frs['total_frs_amt'] != i.total_frs['total_actual_amt'] or
                    i.total_frs['total_outstanding_amt'] != 0
            ):
                raise TransitionError(
                    [_('Total FR amount needs to equal total actual amount'
                       ', and Total Outstanding DCTs need to equal to 0')]
                )

    # If total_actual_amt_usd >100,000 then PD final review should be approved
    if i.total_frs['total_actual_amt_usd'] >= 100000 and not i.final_review_approved:
        raise TransitionError([
            _('Final Review must be approved for documents having amount transferred greater than 100,000')
        ])

    # TODO: figure out Action Point Validation once the spec is completed

    if i.has_active_amendment(InterventionAmendment.KIND_NORMAL):
        raise TransitionError([_('Cannot Transition status while adding an amendment')])

    if i.agreement.partner.blocked:
        raise TransitionError([
            _('PD cannot be closed if the Partner is Blocked in Vision')
        ])
    return True


def transition_to_terminated(i):
    from etools.applications.partners.models import InterventionAmendment

    if not i.termination_doc_attachment.exists():
        raise TransitionError([_('Cannot Transition without termination doc attached')])
    if i.has_active_amendment(InterventionAmendment.KIND_NORMAL):
        raise TransitionError([_('Cannot Transition status while adding an amendment')])
    return True


def transition_to_ended(i):
    from etools.applications.partners.models import InterventionAmendment

    if i.termination_doc_attachment.exists():
        raise TransitionError([_('Cannot Transition to ended if termination_doc attached')])
    if i.has_active_amendment(InterventionAmendment.KIND_NORMAL):
        raise TransitionError([_('Cannot Transition status while adding an amendment')])

    if i.agreement.partner.blocked:
        raise TransitionError([
            _('PD cannot transition to ended if the Partner is Blocked in Vision')
        ])

    return True


def transition_to_suspended(i):
    from etools.applications.partners.models import InterventionAmendment

    if i.has_active_amendment(InterventionAmendment.KIND_NORMAL):
        raise TransitionError([_('Cannot Transition status while adding an amendment')])

    if i.agreement.partner.blocked:
        raise TransitionError([
            _('PD cannot be suspended if the Partner is Blocked in Vision')
        ])

    return True


def transition_to_review(i):
    return True


def transition_to_cancelled(i):
    if not i.cancel_justification:
        raise TransitionError([_('Justification required for cancellation')])
    return True


def transition_to_signature(i):
    # TODO ensure final partnership review document is set
    # this field is part of PR 2769
    return True


def transition_to_signed(i):
    from etools.applications.partners.models import Agreement, InterventionAmendment

    if i.has_active_amendment(InterventionAmendment.KIND_NORMAL):
        raise TransitionError([_('Cannot Transition status while adding an amendment')])

    if i.document_type in [i.PD, i.SPD] and i.agreement.status in [Agreement.SUSPENDED, Agreement.TERMINATED,
                                                                   Agreement.DRAFT]:
        raise TransitionError([_('The PCA related to this record is Draft, Suspended or Terminated. '
                                 'This Programme Document will not change status until the related PCA '
                                 'is in Signed status')])

    if i.agreement.partner.blocked:
        raise TransitionError([
            _('PD cannot transition to signed if the Partner is Blocked in Vision')
        ])

    return True


def transition_to_active(i):
    # Only transitional validation

    # this validation needs to be here in order to attempt the next auto transitional validation
    if i.termination_doc_attachment.exists():
        raise TransitionError([_('Cannot Transition to ended if termination_doc attached')])

    # Validation id 1 -> if intervention is PD make sure the agreement is in active status
    if i.document_type in [i.PD, i.SPD] and i.agreement.status != i.agreement.SIGNED:
        raise TransitionError([
            _('PD cannot be activated if the associated Agreement is not active')
        ])

    if i.agreement.partner.blocked:
        raise TransitionError([
            _('PD cannot be activated if the Partner is Blocked in Vision')
        ])
    return True


def start_end_dates_valid(i):
    # i = intervention
    if i.start and i.end and \
            i.end < i.start:
        return False
    return True


def start_date_signed_valid(i):
    # i = intervention
    if i.in_amendment:
        return True
    if i.signed_by_unicef_date and i.signed_by_partner_date and i.start and (i.signed_pd_document or i.signed_pd_attachment):
        if i.start < max([i.signed_by_unicef_date, i.signed_by_partner_date]):
            return False
    return True


def start_date_related_agreement_valid(i):
    # i = intervention
    if i.in_amendment:
        return True
    if i.document_type in [i.PD, i.SPD] and not i.contingency_pd and i.start and i.agreement.start and \
            (i.signed_pd_document or i.signed_pd_attachment) and i.start < i.agreement.start:
        return False
    return True


def signed_date_valid(i):
    # i = intervention
    today = date.today()
    if (i.signed_by_partner_date and i.signed_by_partner_date > today) or \
            (i.signed_by_unicef_date and i.signed_by_unicef_date > today):
        return False
    return True


def document_type_pca_valid(i):
    """
        Checks if pd has an agreement of type PCA
    """
    if i.document_type in [i.PD, i.SPD] and i.agreement.agreement_type != i.agreement.PCA:
        return False
    return True


# validation id 2
def ssfa_agreement_has_no_other_intervention(i):
    """
    checks if SSFA intervention has an SSFA agreement connected. also checks if it's
    the only intervention for that ssfa agreement
    """
    if i.document_type == i.SSFA:
        if not (i.agreement.agreement_type == i.agreement.SSFA):
            raise BasicValidationError(_('Agreement selected is not of type SSFA'))
        return i.agreement.interventions.count() <= 1
    return True


def rigid_in_amendment_flag(i):
    if i.old_instance and i.in_amendment is True and i.old_instance.in_amendment is False:
        return False
    return True


def sections_valid(i):
    ainds = AppliedIndicator.objects.filter(
        lower_result__result_link__intervention__pk=i.pk).select_related('section')
    ind_sections = set()
    for ind in ainds:
        ind_sections.add(ind.section)
    intervention_sections = set(s for s in i.sections.all())
    if not ind_sections.issubset(intervention_sections):
        draft_status_err = _(' without deleting the indicators first') if i.status == i.DRAFT else ''
        raise BasicValidationError(
            _('The following sections have been selected on the PD/SPD indicators and cannot be removed '
              '%(sections)s ') % {'sections': draft_status_err + ', '.join([s.name for s in ind_sections - intervention_sections])})
    return True


def locations_valid(i):
    ainds = AppliedIndicator.objects.filter(
        lower_result__result_link__intervention__pk=i.pk).prefetch_related('locations')
    ind_locations = set()
    for ind in ainds:
        for loc in ind.locations.all():
            ind_locations.add(loc)
    intervention_locations = set(i.flat_locations.all())
    if not ind_locations.issubset(intervention_locations):
        raise BasicValidationError(
            _('The following locations have been selected on the PD/SPD indicators and '
              'cannot be removed without removing them from the indicators first: %(locations)s') %
            {'locations': ', '.join([str(loc) for loc in ind_locations - intervention_locations])})
    return True


def cp_structure_valid(i):
    if i.agreement.agreement_type == i.agreement.PCA:
        invalid = False
        if i.country_programme:
            if i.country_programme != i.agreement.country_programme:
                invalid = True
        if i.country_programmes.count():
            if i.agreement.country_programme not in i.country_programmes.all():
                invalid = True

        if invalid:
            raise BasicValidationError(
                _('The Country Programme selected on this PD is not the same as the Country Programme selected '
                  'on the Agreement, please select %(cp)s') % {'cp': i.agreement.country_programme})
    return True


def pd_outputs_present(i):
    return i.result_links.exists()


def pd_outputs_are_linked_to_indicators(i):
    return not i.result_links.filter(ll_results__applied_indicators__isnull=True)


def all_pd_outputs_are_associated(i):
    return not i.result_links.filter(cp_output__isnull=True).exists()


def all_activities_have_timeframes(i):
    return not InterventionActivity.objects.\
        filter(result__result_link__intervention=i).\
        filter(time_frames__isnull=True).exists()


def review_was_accepted(i):
    from etools.applications.partners.models import InterventionReview

    r = i.review
    if r.review_type == InterventionReview.NORV:
        return True

    return r.overall_approval if r else False


class InterventionValid(CompleteValidation):
    VALIDATION_CLASS = 'partners.Intervention'
    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [
        ssfa_agreement_has_no_other_intervention,
        start_end_dates_valid,
        signed_date_valid,
        start_date_signed_valid,
        start_date_related_agreement_valid,
        document_type_pca_valid,
        rigid_in_amendment_flag,
        sections_valid,
        locations_valid,
        cp_structure_valid,
    ]

    VALID_ERRORS = {
        'suspended_expired_error': _('State suspended cannot be modified since the end date of '
                                     'the intervention surpasses today'),
        'start_end_dates_valid': _('Start date must precede end date'),
        'signed_date_valid': _('Signatures cannot be dated in the future'),
        'document_type_pca_valid': _('Document type PD or HPD can only be associated with a PCA agreement.'),
        'ssfa_agreement_has_no_other_intervention': _('The agreement selected has at least one '
                                                      'other SSFA Document connected'),
        'start_date_signed_valid': _('The start date cannot be before the later of signature dates.'),
        'start_date_related_agreement_valid': _('PD start date cannot be earlier than the Start Date of the related PCA'),
        'rigid_in_amendment_flag': _('Amendment Flag cannot be turned on without adding an amendment'),
        'sections_valid': _("The sections selected on the PD/SPD are not a subset of all sections selected "
                            "for this PD/SPD's indicators"),
        'locations_valid': _("The locations selected on the PD/SPD are not a subset of all locations selected "
                             "for this PD/SPD's indicators"),
    }

    PERMISSIONS_CLASS = InterventionPermissions

    def check_required_fields(self, intervention):
        required_fields = [f for f in self.permissions['required'] if self.permissions['required'][f] is True]
        required_valid, fields = check_required_fields(intervention, required_fields)
        if not required_valid:
            raise DetailedStateValidationError(
                'required_in_status',
                _('Required fields not completed in %(status)s: %(fields)s') %
                {'status': intervention.status, 'fields': ', '.join(f for f in fields)},
                {'fields': fields, 'status': intervention.status},
            )

    def check_rigid_fields(self, intervention, related=False):
        # this can be set if running in a task and old_instance is not set
        if self.disable_rigid_check:
            return
        rigid_fields = [f for f in self.permissions['edit'] if self.permissions['edit'][f] is False]
        rigid_valid, field = check_rigid_fields(intervention, rigid_fields, related=related)
        if not rigid_valid:
            raise StateValidationError([
                _('Cannot change fields while in %(status)s: %(field)s') % {'status': intervention.status, 'field': field}])

    def state_draft_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        if intervention.unicef_accepted or intervention.partner_accepted:
            if not all_activities_have_timeframes(intervention):
                raise StateValidationError([_('All activities must have at least one time frame')])
            if not pd_outputs_present(intervention):
                raise StateValidationError([_('Results section is empty')])
            if not pd_outputs_are_linked_to_indicators(intervention):
                raise StateValidationError([_('All PD Outputs need to have at least one indicator')])
            if not intervention.planned_budget.total_unicef_contribution_local():
                raise StateValidationError([_('Total UNICEF Contribution must be greater than 0')])
        if intervention.unicef_accepted:
            if not all_pd_outputs_are_associated(intervention):
                raise StateValidationError([_('All PD Outputs need to be associated to a CP Output')])
        return True

    def state_review_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        if not (intervention.partner_accepted and intervention.unicef_accepted):
            raise StateValidationError([_('Unicef and Partner both need to accept')])
        if not all_activities_have_timeframes(intervention):
            raise StateValidationError([_('All activities must have at least one time frame')])
        if not all_pd_outputs_are_associated(intervention):
            raise StateValidationError([_('All PD Outputs need to be associated to a CP Output')])
        return True

    def state_signature_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        if not review_was_accepted(intervention):
            raise StateValidationError([_('Review needs to be approved')])
        return True

    def state_signed_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        if not all_activities_have_timeframes(intervention):
            raise StateValidationError([_('All activities must have at least one time frame')])
        if not all_pd_outputs_are_associated(intervention):
            raise StateValidationError([_('All PD Outputs need to be associated to a CP Output')])
        if intervention.contingency_pd is False and intervention.total_unicef_budget == 0:
            raise StateValidationError([_('UNICEF Cash $ or UNICEF Supplies $ should not be 0')])
        return True

    def state_suspended_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        return True

    def state_active_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        if intervention.in_amendment:
            raise StateValidationError([_('Only original PD can be active')])
        if not all_activities_have_timeframes(intervention):
            raise StateValidationError([_('All activities must have at least one time frame')])
        if not all_pd_outputs_are_associated(intervention):
            raise StateValidationError([_('All PD Outputs need to be associated to a CP Output')])
        today = date.today()
        if not (intervention.start <= today):
            raise StateValidationError([_('Today is not after the start date')])
        if intervention.total_unicef_budget == 0:
            raise StateValidationError([_('UNICEF Cash $ or UNICEF Supplies $ should not be 0')])
        return True

    def state_ended_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        if not all_activities_have_timeframes(intervention):
            raise StateValidationError([_('All activities must have at least one time frame')])
        if not all_pd_outputs_are_associated(intervention):
            raise StateValidationError([_('All PD Outputs need to be associated to a CP Output')])

        today = date.today()
        if not today > intervention.end:
            raise StateValidationError([_('Today is not after the end date')])
        return True

    def map_errors(self, errors):
        error_list = []
        for error in errors:
            if isinstance(error, str):
                error_value = self.VALID_ERRORS.get(error, error)
                if isinstance(error_value, str):
                    error_list.append(_(error_value))
                else:
                    error_list.append(error_value)
            else:
                error_list.append(error)
        return error_list
