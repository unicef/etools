from __future__ import unicode_literals

import logging
from datetime import date

from django.utils.translation import ugettext as _

from EquiTrack.validation_mixins import TransitionError, CompleteValidation, check_rigid_fields, StateValidError, \
    check_required_fields, BasicValidationError
from partners.permissions import AgreementPermissions


def agreement_transition_to_signed_valid(agreement):
    '''Returns True if it's valid for the agreement to transition to signed, otherwise raises a TransitionError.

    TransitionErrors are raised under 3 circumstances --
      - If the agreement is of type PCA and matches certain criteria (see code)
      - If the start date is empty or in the future
      - If the end date is empty or in the past
    '''
    today = date.today()
    if agreement.agreement_type == agreement.PCA and \
            agreement.__class__.objects.filter(partner=agreement.partner,
                                               status=agreement.SIGNED,
                                               agreement_type=agreement.PCA,
                                               country_programme=agreement.country_programme,
                                               start__gt=date(2015, 7, 1)).exists():

        raise TransitionError(['agreement_transition_to_active_invalid_PCA'])

    if not agreement.start or agreement.start > today:
        raise TransitionError(['Agreement cannot transition to signed until '
                               'the start date is less than or equal to today'])
    if not agreement.end or agreement.end < today:
        raise TransitionError(['Agreement cannot transition to signed unless the end date is today or after'])

    return True


def agreement_transition_to_ended_valid(agreement):
    today = date.today()
    logging.debug('I GOT CALLED to ended')
    if agreement.status == agreement.SIGNED and agreement.end and agreement.end < today:
        return True
    raise TransitionError(['agreement_transition_to_ended_invalid'])


def agreements_illegal_transition(agreement):
    return False


def agreements_illegal_transition_permissions(agreement, user):
    logging.debug(agreement.old_instance)
    logging.debug(user)
    # The type of validation that can be done on the user:
    # if user.first_name != 'Rob':
    #     raise TransitionError(['user is not Rob'])
    return True


def amendments_valid(agreement):
    today = date.today()
    for a in agreement.amendments.all():
        if not getattr(a.signed_amendment, 'name'):
            return False
        if not a.signed_date or a.signed_date > today:
            return False
    return True


def start_end_dates_valid(agreement):
    if agreement.start and agreement.end and agreement.start > agreement.end:
        return False
    return True


def signed_by_everyone_valid(agreement):
    if not agreement.signed_by_partner_date and agreement.signed_by_unicef_date:
        return False
    return True


def signatures_valid(agreement):
    today = date.today()
    unicef_signing_requirements = [agreement.signed_by_unicef_date, agreement.signed_by]
    partner_signing_requirements = [agreement.signed_by_partner_date, agreement.partner_manager]
    if agreement.agreement_type == agreement.SSFA:
        if any(unicef_signing_requirements + partner_signing_requirements):
            raise BasicValidationError(_('SSFA signatures are captured at the Document (TOR) level, please clear the '
                                         'signatures and dates and add them to the TOR'))
    unicef_signing_requirements = [agreement.signed_by_unicef_date, agreement.signed_by]
    partner_signing_requirements = [agreement.signed_by_partner_date, agreement.partner_manager]
    if (any(unicef_signing_requirements) and not all(unicef_signing_requirements)) or \
            (any(partner_signing_requirements) and not all(partner_signing_requirements)) or \
            (agreement.signed_by_partner_date and agreement.signed_by_partner_date > today) or \
            (agreement.signed_by_unicef_date and agreement.signed_by_unicef_date > today):
        return False
    return True


def partner_type_valid_cso(agreement):
    if agreement.agreement_type in ["PCA", "SSFA"] and agreement.partner \
            and not agreement.partner.partner_type == "Civil Society Organization":
        return False
    return True


def ssfa_static(agreement):
    if agreement.agreement_type == agreement.SSFA:
        if agreement.interventions.all().exists():
            # there should be only one.. there is a different validation that ensures this
            intervention = agreement.interventions.all().first()
            if intervention.start != agreement.start or intervention.end != agreement.end:
                raise BasicValidationError(_("Start and end dates don't match the Document's start and end"))
    return True


def one_pca_per_cp_per_partner(agreement):
    if agreement.agreement_type == agreement.PCA:
        # see if there are any PCAs in the CP other than this for this partner and started after july 2015
        if agreement.__class__.objects.filter(partner=agreement.partner,
                                              agreement_type=agreement.PCA,
                                              country_programme=agreement.country_programme,
                                              start__gt=date(2015, 7, 1)
                                              ).exclude(pk=agreement.id).exists():
            return False
    return True


class AgreementValid(CompleteValidation):

    VALIDATION_CLASS = 'partners.Agreement'

    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [
        start_end_dates_valid,
        signatures_valid,
        partner_type_valid_cso,
        one_pca_per_cp_per_partner,
        amendments_valid,
        ssfa_static
    ]

    VALID_ERRORS = {
        'one_pca_per_cp_per_partner': 'A PCA with this partner already exists for this Country Programme Cycle. '
                                      'If the record is in "Draft" status please edit that record.',
        'start_end_dates_valid': 'Agreement start date needs to be earlier than or the same as the end date',
        'signatures_valid': 'None of the dates can be in the future; '
                            'If dates are set, signatories are required',
        'generic_transition_fail': 'GENERIC TRANSITION FAIL',
        'agreement_transition_to_active_invalid_PCA': "You cannot have more than 1 PCA active per Partner within 1 CP",
        'partner_type_valid_cso': 'Partner type must be CSO for PCA or SSFA agreement types.',
        'amendments_valid': {'signed_amendment': ['Please check that the Document is attached and'
                                                  ' signatures are not in the future']},
    }

    PERMISSIONS_CLASS = AgreementPermissions

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

    def state_draft_valid(self, agreement, user=None):
        # for SSFAs there will be no states valid since the states are forced by the Interventions
        # Once signed, nothing will be editable on the agreement level
        self.check_required_fields(agreement)
        self.check_rigid_fields(agreement, related=True)
        return True

    def state_signed_valid(self, agreement, user=None):
        # for SSFAs there will be no states valid since the states are forced by the Interventions
        # Once signed, nothing will be editable on the agreement level
        if agreement.agreement_type == agreement.SSFA:
            return False
        self.check_required_fields(agreement)
        self.check_rigid_fields(agreement, related=True)
        return True

    def state_suspended_valid(self, agreement, user=None):
        # for SSFAs there will be no states valid since the states are forced by the Interventions
        # Once signed, nothing will be editable on the agreement level
        if agreement.agreement_type == agreement.SSFA:
            raise StateValidError([_('Please unsuspend the SSFA on the PD/SSFA Page and the record on the Agreement '
                                     'page will be unsuspended automatically.')])

    def state_ended_valid(self, agreement, user=None):
        # for SSFAs there will be no states valid since the states are forced by the Interventions
        # Once signed, nothing will be editable on the agreement level
        if agreement.agreement_type == agreement.SSFA:
            return False

        self.check_required_fields(agreement)
        self.check_rigid_fields(agreement, related=True)
        today = date.today()
        if not today > agreement.end:
            raise StateValidError([_('Today is not after the end date')])
        return True
