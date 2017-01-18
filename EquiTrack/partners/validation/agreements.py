from datetime import date, datetime

from django_fsm import can_proceed, has_transition_perm, get_available_FIELD_transitions

from django.utils.functional import cached_property

valid_errors = {
    'signed_date_valid': 'Signed date cannot be greater than today',
    'transitional_one': 'Cannot Transition to draft',
    'transitional_two': 'Cannot Transition to blah blah',
    'generic_transition_fail': 'GENERIC TRANSITION FAIL'
}

class TransitionError(Exception):
    def __init__(self, message=''):
        super(TransitionError, self).__init__(message)


def error_string(function):
    def wrapper(*args, **kwargs):
        valid = function(*args, **kwargs)
        if valid and type(valid) is bool:
            return (True, [])
        else:
            return (False, [valid_errors[function.__name__]])
    return wrapper


def transition_error_string(function):
    def wrapper(*args, **kwargs):
        try:
            valid = function(*args, **kwargs)
        except TransitionError as e:
            return (False, [valid_errors.get(e.message, e.message)])

        if valid and type(valid) is bool:
            return (True, [])
        else:
            return (False, [valid_errors['generic_transition_fail']])
    return wrapper


def illegal_transition(agreement, *args, **kwargs):
    if True:
        raise TransitionError('transitional_twos')

    return False

def illegal_transition_permissions(agreement, user):

    return False



def signed_date_valid(agreement):
    now = date.today()
    if agreement.signed_by_unicef_date > now or agreement.signed_by_partner_date > now:
        return False
    return True



class CompleteValidation(object):
    def __init__(self, new, old, user):
        self.new = new
        self.new_status = self.new.status
        self.old = old
        self.old_status = self.old.status
        self.user = user

    def check_transition_conditions(self, transition):
        if not transition:
            return True
        return can_proceed(transition)

    def check_transition_permission(self, transition):
        if not transition:
            return True
        return has_transition_perm(transition, self.user)

    @cached_property
    def transition(self):
        # TODO: try to get the transitions in a better way
        # print [i for i in get_available_FIELD_transitions(self.old, self.old.__class__._meta.get_field('status'))]
        # transitions = list(self.old.__class__._meta.get_field('status').get_all_transitions(self.old.__class__))
        # transitions = self.old.__class__._meta.get_field('status').transitions
        # print 'transitions:', transitions.get('active', None)

        for obj in self.transitions:
            if self.old_status in obj['from']:
                if self.new_status in obj['to']:
                    return getattr(self.new, obj['transition_function'])
        return None

    @transition_error_string
    def transitional_validation(self):
        # set old status to get proper transitions
        self.new.status = self.old.status

        # set old instance on instance to make it available to the validation functions
        setattr(self.new, 'old_instance', self.old)

        # check conditions and permissions

        conditions_check = self.check_transition_conditions(self.transition)

        permissions_check = self.check_transition_permission(self.transition)

        # cleanup
        delattr(self.new, 'old_instance')
        self.new.status = self.new_status
        return conditions_check and permissions_check

    @cached_property
    def basic_validation(self):
        '''
        basic set of validations to make sure new state is correct
        :return: True or False
        '''
        errors = []
        for function in self.BASIC_VALIDATIONS:
            a = error_string(function)(self.new)
            errors = a[1]
        return not len(errors), errors

    @cached_property
    def total_validation(self):
        if not self.basic_validation[0]:
            return (False, self.basic_validation[1])
        return self.transitional_validation()

    @property
    def is_valid(self):
        return self.total_validation[0]

    @property
    def errors(self):
        return self.total_validation[1]


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
    BASIC_VALIDATIONS = [signed_date_valid]






