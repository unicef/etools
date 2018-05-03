
import logging
from datetime import date

from django.utils import six
from django.utils.translation import ugettext as _

from etools.applications.EquiTrack.validation_mixins import (BasicValidationError, check_required_fields,
                                                             check_rigid_fields, CompleteValidation,
                                                             StateValidError, TransitionError,)
from etools.applications.partners.permissions import InterventionPermissions
from etools.applications.reports.models import AppliedIndicator

logger = logging.getLogger('partners.interventions.validation')


def partnership_manager_only(i, user):
    # Transition cannot happen by a user that's not a Partnership Manager
    if not user.groups.filter(name__in=['Partnership Manager']).count():
        raise TransitionError(['Only Partnership Managers can execute this transition'])
    return True


def transition_ok(i):
    return True


def transition_to_closed(i):
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
        'latest_end_date': None
    }
    for fr in i.frs.filter():
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

    if i.total_frs['total_frs_amt'] != i.total_frs['total_actual_amt'] or \
            i.total_frs['total_outstanding_amt'] != 0:
        raise TransitionError([_('Total FR amount needs to equal total actual amount, and '
                                 'Total Outstanding DCTs need to equal to 0')])

    # If total_actual_amt_usd >100,000 then attachments has to include
    # at least 1 record with type: "Final Partnership Review"
    if i.total_frs['total_actual_amt_usd'] >= 100000:
        if i.attachments.filter(type__name='Final Partnership Review').count() < 1:
            raise TransitionError([_('Total amount transferred greater than 100,000 and no Final Partnership Review '
                                     'was attached')])

    # TODO: figure out Action Point Validation once the spec is completed

    if i.in_amendment is True:
        raise TransitionError([_('Cannot Transition status while adding an amendment')])
    return True


def transition_to_terminated(i):
    if i.in_amendment is True:
        raise TransitionError([_('Cannot Transition status while adding an amendment')])

    return True


def transition_to_ended(i):
    if i.in_amendment is True:
        raise TransitionError([_('Cannot Transition status while adding an amendment')])

    return True


def transition_to_suspended(i):
    if i.in_amendment is True:
        raise TransitionError([_('Cannot Transition status while adding an amendment')])

    return True


def transition_to_signed(i):
    from etools.applications.partners.models import Agreement
    if i.in_amendment is True:
        raise TransitionError([_('Cannot Transition status while adding an amendment')])
    if i.document_type in [i.PD, i.SHPD] and i.agreement.status in [Agreement.SUSPENDED, Agreement.TERMINATED]:
        raise TransitionError([_('The PCA related to this record is Suspended or Terminated. '
                                 'This Programme Document will not change status until the related PCA '
                                 'is in Signed status')])

    if i.in_amendment is True:
        raise TransitionError([_('Cannot Transition status while adding an amendment')])

    return True


def transition_to_active(i):
    # Only transitional validation

    # Validation id 1 -> if intervention is PD make sure the agreement is in active status
    if i.document_type in [i.PD, i.SHPD] and i.agreement.status != i.agreement.SIGNED:
        raise TransitionError([
            _('PD cannot be activated if the associated Agreement is not active')
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
    if i.signed_by_unicef_date and i.signed_by_partner_date and i.start and i.signed_pd_document:
        if i.start < max([i.signed_by_unicef_date, i.signed_by_partner_date]):
            return False
    return True


def start_date_related_agreement_valid(i):
    # i = intervention
    if i.document_type in [i.PD, i.SHPD] and not i.contingency_pd and i.start and i.agreement.start and \
            i.signed_pd_document and i.start < i.agreement.start:
        return False
    return True


def signed_date_valid(i):
    # i = intervention
    today = date.today()
    unicef_signing_requirements = [i.signed_by_unicef_date, i.unicef_signatory]
    partner_signing_requirements = [i.signed_by_partner_date, i.partner_authorized_officer_signatory]
    if (any(unicef_signing_requirements) and not all(unicef_signing_requirements)) or \
            (any(partner_signing_requirements) and not all(partner_signing_requirements)) or \
            (i.signed_by_partner_date and i.signed_by_partner_date > today) or \
            (i.signed_by_unicef_date and i.signed_by_unicef_date > today):
        return False
    return True


def document_type_pca_valid(i):
    '''
        Checks if pd has an agreement of type PCA
    '''
    if i.document_type in [i.PD, i.SHPD] and i.agreement.agreement_type != i.agreement.PCA:
        return False
    return True


# validation id 2
def ssfa_agreement_has_no_other_intervention(i):
    '''
    checks if SSFA intervention has an SSFA agreement connected. also checks if it's
    the only intervention for that ssfa agreement
    '''
    if i.document_type == i.SSFA:
        if not(i.agreement.agreement_type == i.agreement.SSFA):
            raise BasicValidationError(_('Agreement selected is not of type SSFA'))
        return i.agreement.interventions.all().count() <= 1
    return True


def rigid_in_amendment_flag(i):
    if i.old_instance and i.in_amendment is True and i.old_instance.in_amendment is False:
        return False
    return True


def sections_valid(i):
    ainds = AppliedIndicator.objects.filter(lower_result__result_link__intervention__pk=i.pk).all()
    ind_sections = set()
    for ind in ainds:
        ind_sections.add(ind.section)
    intervention_sections = set(s for s in i.sections.all())
    if not ind_sections.issubset(intervention_sections):
        draft_status_err = ' without deleting the indicators first' if i.status == i.DRAFT else ''
        raise BasicValidationError(_('The following sections have been selected on '
                                     'the PD/SSFA indicators and cannot be removed{}: '.format(draft_status_err)) +
                                   ', '.join([s.name for s in ind_sections - intervention_sections]))
    return True


def locations_valid(i):
    ainds = AppliedIndicator.objects.filter(lower_result__result_link__intervention__pk=i.pk).all()
    ind_locations = set()
    for ind in ainds:
        for l in ind.locations.all():
            ind_locations.add(l)
    intervention_locations = set(i.flat_locations.all())
    if not ind_locations.issubset(intervention_locations):
        raise BasicValidationError(_('The following locations have been selected on '
                                     'the PD/SSFA indicators and cannot be removed'
                                     ' without removing them from the indicators first: ') +
                                   ', '.join([six.text_type(l) for l in ind_locations - intervention_locations]))
    return True


def cp_structure_valid(i):
    if i.country_programme and i.agreement.agreement_type == i.agreement.PCA \
            and i.country_programme != i.agreement.country_programme:
        raise BasicValidationError(_('The Country Programme selected on this PD is not the same as the '
                                     'Country Programme selected on the Agreement, '
                                     'please select "{}"'.format(i.agreement.country_programme)))
    return True


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
        'suspended_expired_error': 'State suspended cannot be modified since the end date of '
                                   'the intervention surpasses today',
        'start_end_dates_valid': 'Start date must precede end date',
        'signed_date_valid': 'Unicef signatory and partner signatory as well as dates required, '
                             'signatures cannot be dated in the future',
        'document_type_pca_valid': 'Document type PD or SHPD can only be associated with a PCA agreement.',
        'ssfa_agreement_has_no_other_intervention': 'The agreement selected has at least one '
                                                    'other SSFA Document connected',
        'start_date_signed_valid': 'The start date cannot be before the later of signature dates.',
        'start_date_related_agreement_valid': 'PD start date cannot be earlier than the Start Date of the related PCA',
        'rigid_in_amendment_flag': 'Amendment Flag cannot be turned on without adding an amendment',
        'sections_valid': "The sections selected on the PD/SSFA are not a subset of all sections selected "
                          "for this PD/SSFA's indicators",
        'locations_valid': "The locations selected on the PD/SSFA are not a subset of all locations selected "
                          "for this PD/SSFA's indicators",
    }

    PERMISSIONS_CLASS = InterventionPermissions

    def check_required_fields(self, intervention):
        required_fields = [f for f in self.permissions['required'] if self.permissions['required'][f] is True]
        required_valid, fields = check_required_fields(intervention, required_fields)
        if not required_valid:
            raise StateValidError(['Required fields not completed in {}: {}'.format(
                intervention.status, ', '.join(f for f in fields))])

    def check_rigid_fields(self, intervention, related=False):
        # this can be set if running in a task and old_instance is not set
        if self.disable_rigid_check:
            return
        rigid_fields = [f for f in self.permissions['edit'] if self.permissions['edit'][f] is False]
        rigid_valid, field = check_rigid_fields(intervention, rigid_fields, related=related)
        if not rigid_valid:
            raise StateValidError(['Cannot change fields while in {}: {}'.format(intervention.status, field)])

    def state_draft_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        return True

    def state_signed_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        if intervention.total_unicef_budget == 0:
            raise StateValidError([_('UNICEF Cash $ or UNICEF Supplies $ should not be 0')])
        return True

    def state_suspended_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        return True

    def state_active_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)

        today = date.today()
        if not (intervention.start <= today):
            raise StateValidError([_('Today is not after the start date')])
        if intervention.total_unicef_budget == 0:
            raise StateValidError([_('UNICEF Cash $ or UNICEF Supplies $ should not be 0')])
        return True

    def state_ended_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)

        today = date.today()
        if not today > intervention.end:
            raise StateValidError([_('Today is not after the end date')])
        return True
