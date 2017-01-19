from datetime import date, datetime

from EquiTrack.validation_mixins import TransitionError, CompleteValidation



def illegal_transition(agreement):
    print agreement.old_instance
    if True:
        raise TransitionError(['transitional_two'])

    return False

def continion_one_for_transition_X(agreement):
    pass

def illegal_transition_permissions(agreement, user):
    print agreement.old_instance
    print user
    return False


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
    if agreement.signed_by_unicef_date > now or agreement.signed_by_partner_date > now:
        return False
    return True

def signed_boo_valid(agreement):
    now = date.today()
    if agreement.signed_by_unicef_date > now or agreement.signed_by_partner_date > now:
        return False
    return True

def signed_by_everyone_valid(agreement):
    if not agreement.signed_by_partner_date and agreement.signed_by_unicef_date:
        return False
    return True

class AgreementValid(CompleteValidation):


    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [signed_date_valid, signed_boo_valid]
    VALID_ERRORS = {
        'signed_date_valid': 'Signed date cannot be greater than today',
        'signed_boo_valid': 'Boo date cannot be greater than today',
        'transitional_one': 'Cannot Transition to draft',
        'transitional_two': 'Cannot Transition to blah blah',
        'generic_transition_fail': 'GENERIC TRANSITION FAIL',
        'suspended_invalid': 'hey can;t suspend an agreement that was supposed to be ended'
    }

    def state_suspended_valid(self, agreement):
        if agreement.to_date > date.today:
            return False, ['suspended_invalid']

    def state_active_valid(self, agreement):
        pass









