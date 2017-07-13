from __future__ import unicode_literals
from datetime import date, datetime
import logging

from django.utils.translation import ugettext as _


from EquiTrack.validation_mixins import TransitionError, CompleteValidation, StateValidError, check_rigid_related, \
    BasicValidationError, check_rigid_fields, check_required_fields
from partners.permissions import InterventionPermissions

logger = logging.getLogger('partners.interventions.validation')


def partnership_manager_only(i, user):
    # Transition cannot happen by a user that';s not a Partnership Manager
    if not user.groups.filter(name__in=['Partnership Manager']).count():
        raise TransitionError(['Only Partnership Managers can execute this transition'])
    return True


def transition_ok(i):
    return True


def transition_to_closed(i):
    # validation id 6

    # Make sure that is past the end date
    today = date.today()
    if i.end > today:
        raise TransitionError([_('End date is in the future')])

    if i.total_frs_amt['total_intervention_amt'] != i.total_frs_amt['total_actual_amt'] or \
            i.total_frs_amt['total_outstanding_amt'] != 0:
        raise TransitionError([_('Total FR amount needs to equal total actual amount, and'
                                 'Total Outstanding DCTs need to equal to 0')])

    # If total_actual_amt >100,000 then attachments has to include
    # at least 1 record with type: "Final Partnership Review"
    if i.total_frs_amt['total_actual_amt'] > 100000:
        if i.attachments.filter(type__name='final partnership review').count() < 1:
            raise TransitionError([_('Total amount transferred greater than 100,000 and no Final Partnership Review '
                                     'was attached')])

    # TODO: figure out Action Point Validation once the spec is completed

    return True

def transition_to_active(i):
    # Only transitional validation

    # Validation id 1 -> if intervention is PD make sure the agreement is in active status
    if i.document_type == i.PD and i.agreement.status != i.agreement.SIGNED:
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


def signed_date_valid(i):
    # i = intervention
    today = date.today()
    if (i.signed_by_unicef_date and not i.unicef_signatory) or \
            (i.signed_by_partner_date and not i.partner_authorized_officer_signatory) or \
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


def amendments_valid(i):
    if i.status not in [i.ACTIVE, i.SIGNED] and i.amendments.exists():
        # this prevents any changes in amendments if the status is not in Signed or Active
        if not check_rigid_related(i, 'amendments'):
            return False
    for a in i.amendments.all():
        if a.OTHER in a.types and a.other_description is None:
            return False
        if not a.signed_date:
            return False
        if not getattr(a, a.signed_amendment, 'name'):
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
        document_type_pca_valid,
        amendments_valid,
    ]

    VALID_ERRORS = {
        'suspended_expired_error': 'State suspended cannot be modified since the end date of '
                                   'the intervention surpasses today',
        'start_end_dates_valid': 'Start date must precede end date',
        'signed_date_valid': 'Unicef signatory and partner signatory as well as dates required, '
                             'signatures cannot be dated in the future',
        'document_type_pca_valid': 'Document type PD or SHPD can only be associated with a PCA agreement.',
        'amendments_valid': 'Type, signed date, and signed amendment are required in Amendments. '
                            'If you seleced Other as an amendment type, please add the description',
        'ssfa_agreement_has_no_other_intervention': 'The agreement selected has at least one '
                                                    'other SSFA Document connected'
    }

    PERMISSIONS_CLASS = InterventionPermissions

    def check_required_fields(self, intervention):
        required_fields = [f for f in self.permissions['required'] if self.permissions['required'][f] is True]
        required_valid, field = check_required_fields(intervention, required_fields)
        if not required_valid:
            raise StateValidError(['Required fields not completed in {}: {}'.format(intervention.status, field)])

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

        return True

    def state_suspended_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        return True

    def state_active_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)

        today = date.today()
        if not (intervention.start <= today <= intervention.end):
            raise StateValidError([_('Today is not within the start and end dates')])
        return True

    def state_ended_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)

        today = date.today()
        if not today > intervention.end:
            raise StateValidError([_('Today is not after the end date')])
        return True

