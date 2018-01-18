from __future__ import unicode_literals
from datetime import date
import logging

from django.utils.translation import ugettext as _


from EquiTrack.validation_mixins import TransitionError, CompleteValidation, StateValidError, check_rigid_related, \
    BasicValidationError, check_rigid_fields, check_required_fields

from partners.permissions import InterventionPermissions

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
        'total_outstanding_amt': 0,
        'total_intervention_amt': 0,
        'total_actual_amt': 0,
        'earliest_start_date': None,
        'latest_end_date': None
    }
    for fr in i.frs.filter():
        r['total_frs_amt'] += fr.total_amt
        r['total_outstanding_amt'] += fr.outstanding_amt
        r['total_intervention_amt'] += fr.intervention_amt
        r['total_actual_amt'] += fr.actual_amt
        if r['earliest_start_date'] is None:
            r['earliest_start_date'] = fr.start_date
        elif r['earliest_start_date'] < fr.start_date:
            r['earliest_start_date'] = fr.start_date
        if r['latest_end_date'] is None:
            r['latest_end_date'] = fr.end_date
        elif r['latest_end_date'] > fr.end_date:
            r['latest_end_date'] = fr.end_date
    # hack
    i.total_frs = r

    # Make sure that is past the end date
    today = date.today()
    if i.end > today:
        raise TransitionError([_('End date is in the future')])

    if i.total_frs['total_intervention_amt'] != i.total_frs['total_actual_amt'] or \
            i.total_frs['total_outstanding_amt'] != 0:
        raise TransitionError([_('Total FR amount needs to equal total actual amount, and '
                                 'Total Outstanding DCTs need to equal to 0')])

    # If total_actual_amt >100,000 then attachments has to include
    # at least 1 record with type: "Final Partnership Review"
    if i.total_frs['total_actual_amt'] >= 100000:
        if i.attachments.filter(type__name='Final Partnership Review').count() < 1:
            raise TransitionError([_('Total amount transferred greater than 100,000 and no Final Partnership Review '
                                     'was attached')])

    # TODO: figure out Action Point Validation once the spec is completed

    return True


def transition_to_signed(i):
    from partners.models import Agreement
    if i.document_type in [i.PD, i.SHPD] and i.agreement.status in [Agreement.SUSPENDED, Agreement.TERMINATED]:
        raise TransitionError([_('The PCA related to this record is Suspended or Terminated. '
                                 'This Programme Document will not change status until the related PCA '
                                 'is in Signed status')])
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
        'start_date_related_agreement_valid': 'PD start date cannot be earlier than the Start Date of the related PCA'
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
