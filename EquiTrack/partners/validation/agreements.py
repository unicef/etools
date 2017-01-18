from datetime import date, datetime

from EquiTrack.validation_mixins import TransitionError, CompleteValidation



def illegal_transition(agreement, *args, **kwargs):
    if True:
        raise TransitionError(['transitional_two'])

    return False

def illegal_transition_permissions(agreement, user):

    return False


def signed_date_valid(agreement):
    now = date.today()
    if agreement.signed_by_unicef_date > now or agreement.signed_by_partner_date > now:
        return False
    return True

def signed_boo_valid(agreement):
    now = date.today()
    if agreement.signed_by_unicef_date > now or agreement.signed_by_partner_date > now:
        return False
    return True



class AgreementValid(CompleteValidation):

    # TODO: Django fsm gives us some sort of mapping like this
    transitions = [
        {
            'from': ['active'],
            'to': ['suspended'],
            'transition_function': 'transition_to_suspended'
        }
    ]
    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [signed_date_valid, signed_boo_valid]
    VALID_ERRORS = {
        'signed_date_valid': 'Signed date cannot be greater than today',
        'signed_boo_valid': 'Boo date cannot be greater than today',
        'transitional_one': 'Cannot Transition to draft',
        'transitional_two': 'Cannot Transition to blah blah',
        'generic_transition_fail': 'GENERIC TRANSITION FAIL'
    }







