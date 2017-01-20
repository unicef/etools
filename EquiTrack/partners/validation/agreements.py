from datetime import date, datetime

from EquiTrack.validation_mixins import TransitionError, CompleteValidation, check_rigid_fields, StateValidError

def agreement_transition_to_active_valid(agreement):
    print 'I GOT CALLED to active'
    print agreement.status, agreement.start, agreement.end, agreement.signed_by_partner_date, agreement.signed_by_unicef_date, agreement.signed_by, agreement.partner_manager
    if agreement.status == agreement.DRAFT and agreement.start and agreement.end and \
            agreement.signed_by_unicef_date and agreement.signed_by_partner_date and \
            agreement.signed_by and agreement.partner_manager:
        print "moving to active ok"
        return True
    return False

def agreement_transition_to_ended_valid(agreement):
    today = datetime.date.today()
    print 'I GOT CALLED to ended'
    if agreement.status == agreement.ACTIVE and agreement.end and agreement.end < today:
        return False
    return False

def agreements_illegal_transition(agreement):
    # print agreement.old_instance
    # if True:
    #     raise TransitionError(['transitional_two'])

    return True

def continion_one_for_transition_X(agreement):
    pass

def agreements_illegal_transition_permissions(agreement, user):
    print agreement.old_instance
    print user
    if user.first_name != 'Jim':
        raise TransitionError(['user is not Rob'])
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

def signed_boo_valid(agreement):
    now = date.today()
    # if agreement.signed_by_unicef_date > now or agreement.signed_by_partner_date > now:
    #     return False
    return True

def signed_by_everyone_valid(agreement):
    if not agreement.signed_by_partner_date and agreement.signed_by_unicef_date:
        return False
    return True


class AgreementValid(CompleteValidation):

    VALIDATION_CLASS = 'partners.Agreement'
    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [signed_date_valid, signed_boo_valid]
    VALID_ERRORS = {
        'signed_date_valid': 'Signed date cannot be greater than today',
        'signed_boo_valid': 'Boo date cannot be greater than today',
        'transitional_one': 'Cannot Transition to draft',
        'transitional_two': 'Cannot Transition to blah blah',
        'generic_transition_fail': 'GENERIC TRANSITION FAIL',
        'suspended_invalid': 'hey can;t suspend an agreement that was supposed to be ended',
        'state_active_not_signed': 'Hey this is agreement needs to be signed in order to be active, no signed dates'
    }

    def state_suspended_valid(self, agreement):
        if agreement.end > date.today():
            raise StateValidError('suspended_invalid')
        return True

    def state_active_valid(self, agreement):
        print 'STATE ACTIVE VALID CALLED'
        if not agreement.old_instance:
            raise StateValidError(['no direct active state'])
        if agreement.old_instance and agreement.status == agreement.old_instance.status:
            rigid_fields = ['signed_by_unicef_date']
            valid, changed_field = check_rigid_fields(agreement, rigid_fields)
            if not valid:
                raise StateValidError('rigid_field_changed: %s' % changed_field)

        if not agreement.signed_by_partner_date or not agreement.signed_by_unicef_date:
            raise StateValidError(['state_active_not_signed'])

        return True

    def state_cancelled_valid(self, agreement):
        print 'STATE CANCELLED VALID CALLED'
        return False









