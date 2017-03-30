import logging
from datetime import date, datetime

from EquiTrack.validation_mixins import TransitionError, CompleteValidation, check_rigid_fields, StateValidError
from reports.models import CountryProgramme


def agreement_transition_to_active_valid(agreement):
    if not(agreement.status == agreement.DRAFT and agreement.start and agreement.end and
            agreement.signed_by_unicef_date and agreement.signed_by_partner_date and
            agreement.signed_by and agreement.partner_manager and agreement.country_programme):
        logging.debug("moving to active ok")
        raise TransitionError(['agreement_transition_to_active_invalid'])
    if agreement.agreement_type == agreement.PCA and \
            agreement.__class__.objects.filter(partner=agreement.partner,
                                     status=agreement.ACTIVE,
                                     agreement_type=agreement.PCA,
                                     country_programme=agreement.country_programme).count():

        raise TransitionError(['agreement_transition_to_active_invalid_PCA'])
    return True

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

def start_date_valid(agreement):
    if agreement.start and agreement.end and agreement.start > agreement.end:
        return False
    return True

def end_date_valid(agreement):
    if agreement.start and agreement.end and agreement.start > agreement.end:
        return False
    return True

def end_date_country_programme_valid(agreement):
    if agreement.agreement_type == agreement.PCA and agreement.start and agreement.end:
        try:
            cp = CountryProgramme.encapsulates(agreement.start, agreement.start)
        except CountryProgramme.DoesNotExist:
            return True
        if agreement.end > cp.to_date:
            return False
    return True

def start_date_equals_max_signoff(agreement):
    # if not all dates are present no validation necessary
    if agreement.start and agreement.signed_by_unicef_date and agreement.signed_by_partner_date \
            and agreement.start != max(agreement.signed_by_unicef_date, agreement.signed_by_partner_date):
        return False
    return True


def signed_by_unicef_date_past(agreement):
    '''
    :param agreement:
        agreement - > new agreement
        agreement.old_instance -> old agreement
        agreement.old_instance.amendments_old - > old amendments before the update in list format

    :return:
        True or False / conditions are met
    '''

    now = date.today()
    if agreement.signed_by_unicef_date and agreement.signed_by_unicef_date > now:
        return False
    return True

def signed_by_partner_date_past(agreement):
    now = date.today()
    if agreement.signed_by_partner_date and agreement.signed_by_partner_date > now:
        return False
    return True

def signed_by_valid(agreement):
    if not agreement.signed_by:
        return False
    return True

def signed_by_valid_partner_manager(agreement):
    if not agreement.partner_manager:
        return False
    return True

def signed_by_partner_date_valid(agreement):
    if not agreement.signed_by_partner_date:
        return False
    return True

def signed_by_unicef_date_valid(agreement):
    if not agreement.signed_by_unicef_date:
        return False
    return True

def signed_agreement_present(agreement):

    # if not agreement.attached_agreement:
    #     return False
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
        start_date_valid,
        end_date_valid,
        signed_by_unicef_date_past,
        signed_by_partner_date_past,
        start_date_equals_max_signoff,
        partner_type_valid_cso,
        end_date_country_programme_valid
    ]

    VALID_ERRORS = {
        'signed_agreement_present': {
            'attached_agreement': ['Signed agreement must be included in order to activate']
        },
        'start_date_valid': {
            'start': ['Agreement start date needs to be earlier than end date']
        },
        'end_date_valid': {
            'end': ['Agreement start date needs to be earlier than end date']
        },
        'signed_by_partner_date_valid': {
            'signed_by_partner_date': ['Agreement needs to be signed by Partner']
        },
        'signed_by_unicef_date_valid': {
            'signed_by_unicef_date': ['Agreement needs to be signed by UNICEF']
        },
        'signed_by_unicef_date_past': {
            'signed_by_unicef_date': ['Signed dates cannot be greater than today']
        },
        'signed_by_partner_date_past': {
            'signed_by_partner_date': ['Signed dates cannot be greater than today']
        },
        'suspended_invalid': {
            'status': ['Cant suspend an agreement that was supposed to be ended']
        },
        'state_active_not_signed_partner': {
            'signed_by_partner_date': ['This agreement needs to be signed in order to be active']
        },
        'state_active_not_signed_unicef': {
            'signed_by_unicef_date': ['This agreement needs to be signed in order to be active']
        },
        'agreement_transition_to_active_invalid': {
            'status': ["You can't transition to active without having the proper signatures"]
        },
        'agreement_transition_to_active_invalid_PCA': {
            'status': ["You cannot have more than 1 PCA active per Partner within 1 CP"]
        },
        'cant_create_in_active_state': {
            'status': ['When adding a new object the state needs to be "Draft"']
        },
        'start_date_equals_max_signoff': {
            'start': ['Start date must equal to the most recent signoff date (either signed_by_unicef_date or signed_by_partner_date).']
        },
        'partner_type_valid_cso': {
            'partner_type': ['Partner type must be CSO for PCA or SSFA agreement types.']
        },
        'signed_by_valid': {
            'signed_by': ['Signed by UNICEF must be provided']
        },
        'signed_by_valid_partner': {
            'partner_manager': ['Signed by Partner must be provided']
        },
        'end_date_country_programme_valid': {
            'end': ['PCA cannot end after current Country Programme.']
        },
        'transitional_one': 'Cannot Transition to draft',
        'generic_transition_fail': 'GENERIC TRANSITION FAIL',
    }

    def state_suspended_valid(self, agreement, user=None):
        # TODO: figure out when suspended is invalid
        # if agreement.end > date.today():
        #     raise StateValidError('suspended_invalid')
        return True

    def state_active_valid(self, agreement, user=None):
        errors = []
        if not agreement.old_instance:
            errors.append('cant_create_in_active_state')

        if not signed_by_partner_date_valid(agreement):
            errors.append('signed_by_partner_date_valid')

        if not signed_by_unicef_date_valid(agreement):
            errors.append('signed_by_unicef_date_valid')

        if not signed_by_valid(agreement):
            errors.append('signed_by_valid')

        if not signed_agreement_present(agreement):
            errors.append('signed_agreement_present')

        if agreement.old_instance and agreement.status == agreement.old_instance.status:
            rigid_fields = []  # this males all fields editable, will remove later
            # rigid_fields = ['signed_by_unicef_date', 'signed_by_partner_date', 'signed_by', 'partner_manager']
            valid, changed_field = check_rigid_fields(agreement, rigid_fields)
            if not valid:
                errors.append('rigid_field_changed: %s' % changed_field)

        if not agreement.signed_by_partner_date:
            errors.append('state_active_not_signed_partner')

        if not agreement.signed_by_unicef_date:
            errors.append('state_active_not_signed_unicef')

        if errors:
            raise StateValidError(errors)

        return True

    def state_cancelled_valid(self, agreement, user=None):
        return False
