import logging
from datetime import date, datetime

from EquiTrack.validation_mixins import TransitionError, CompleteValidation, check_rigid_fields, StateValidError


def agreement_transition_to_active_valid(agreement):
    logging.debug(agreement.status, agreement.start, agreement.end, agreement.signed_by_partner_date, agreement.signed_by_unicef_date, agreement.signed_by, agreement.partner_manager)
    if agreement.status == agreement.DRAFT and agreement.start and agreement.end and \
            agreement.signed_by_unicef_date and agreement.signed_by_partner_date and \
            agreement.signed_by and agreement.partner_manager:
        logging.debug("moving to active ok")
        return True
    raise TransitionError(['agreement_transition_to_active_invalid'])

def agreement_transition_to_ended_valid(agreement):
    today = date.today()
    logging.debug('I GOT CALLED to ended')
    if agreement.status == agreement.ACTIVE and agreement.end and agreement.end < today:
        return True
    raise TransitionError(['agreement_transition_to_ended_invalid'])

def agreements_illegal_transition(agreement):
    # logging.debug(agreement.old_instance)
    # if True:
    #     raise TransitionError(['transitional_two'])
    return False

def agreements_illegal_transition_permissions(agreement, user):
    logging.debug(agreement.old_instance)
    logging.debug(user)
    # The type of validation that can be done on the user:
    # if user.first_name != 'Rob':
    #     raise TransitionError(['user is not Rob'])
    return True

def amendments_ok(agreement):
    old_instance = agreement.old_instance

    # if there is no old instance
    if not old_instance:
        return True

    # if there are no old amendments
    # if not old_instance.amendments_old:
    #     return True

    # To be Continued
    return True

def start_end_dates_valid(agreement):
    if agreement.start and agreement.end and agreement.start > agreement.end:
        return False
    return True

def start_date_equals_max_signoff(agreement):
    dates = [agreement.signed_by_unicef_date, agreement.signed_by_partner_date]
    if agreement.start and agreement.start != max(x for x in dates if x):
        return False
    return True

def signed_date_valid(agreement):
    '''
    :param agreement:
        agreement - > new agreement
        agreement.old_instance -> old agreement
        agreement.old_instance.amendments_old - > old amendments before the update in list format

    :return:
        True or False / conditions are met
    '''

    now = date.today()
    if (agreement.signed_by_unicef_date and agreement.signed_by_unicef_date > now) or \
            (agreement.signed_by_partner_date and agreement.signed_by_partner_date > now):
        return False
    return True

def signed_by_valid(agreement):
    if not agreement.signed_by or not agreement.partner_manager:
        return False
    return True

def signed_by_everyone_valid(agreement):
    if not agreement.signed_by_partner_date and agreement.signed_by_unicef_date:
        return False
    return True

def signed_agreement_present(agreement):

    if not agreement.attached_agreement:
        return False
    return True

def partner_type_valid_cso(agreement):
    if agreement.agreement_type in ["PCA", "SSFA"] and agreement.partner \
        and not agreement.partner.partner_type == "Civil Society Organization":
            return False
    return True

class AgreementValid(CompleteValidation):

    # TODO: add user on basic and state

    VALIDATION_CLASS = 'partners.Agreement'
    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [
        start_end_dates_valid,
        signed_date_valid,
        start_date_equals_max_signoff,
        partner_type_valid_cso,
    ]

    VALID_ERRORS = {
        'signed_agreement_present': 'Signed agreement must be included in order to activate',
        'start_end_dates_valid': 'Agreement start date needs to be earlier than end date',
        'signed_by_everyone_valid': 'Agreement needs to be signed by UNICEF and Partner',
        'signed_date_valid': 'Signed dates cannot be greater than today, only magical creatures can sign in the future',
        'transitional_one': 'Cannot Transition to draft',
        'generic_transition_fail': 'GENERIC TRANSITION FAIL',
        'suspended_invalid': 'Cant suspend an agreement that was supposed to be ended',
        'state_active_not_signed': 'This agreement needs to be signed in order to be active, no signed dates',
        'agreement_transition_to_active_invalid': "You can't transition to active without having the proper signatures",
        'cant_create_in_active_state': 'When adding a new object the state needs to be "Draft"',
        'start_date_equals_max_signoff': 'Start date must equal to the most recent signoff date (either signed_by_unicef_date or signed_by_partner_date).',
        'partner_type_valid_cso': 'Partner type must be CSO for PCA or SSFA agreement types.',
        'signed_by_valid': 'Partner manager and signed by must be provided.',
    }

    def state_suspended_valid(self, agreement, user=None):
        # TODO: figure out when suspended is invalid
        # if agreement.end > date.today():
        #     raise StateValidError('suspended_invalid')
        return True

    def state_active_valid(self, agreement, user=None):
        logging.debug('STATE ACTIVE VALID CALLED')
        if not agreement.old_instance:
            raise StateValidError(['cant_create_in_active_state'])

        if not signed_by_everyone_valid(agreement):
            raise StateValidError(['signed_by_everyone_valid'])

        if not signed_by_valid(agreement):
            raise StateValidError(['signed_by_valid'])

        if not signed_agreement_present(agreement):
            raise StateValidError(['signed_agreement_present'])

        if agreement.old_instance and agreement.status == agreement.old_instance.status:
            rigid_fields = ['signed_by_unicef_date', 'signed_by_partner_date', 'signed_by', 'partner_manager']
            valid, changed_field = check_rigid_fields(agreement, rigid_fields)
            if not valid:
                raise StateValidError('rigid_field_changed: %s' % changed_field)

        if not agreement.signed_by_partner_date or not agreement.signed_by_unicef_date:
            raise StateValidError(['state_active_not_signed'])

        return True

    def state_cancelled_valid(self, agreement, user=None):
        logging.debug('STATE CANCELLED VALID CALLED')
        return False
