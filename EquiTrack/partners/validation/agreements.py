from datetime import date, datetime

from django_fsm import can_proceed, has_transition_perm

from django.utils.functional import cached_property

valid_errors = {
    'signed_date_valid': 'Signed date cannot be greater than today',
    'transitional_one': 'Cannot Transition to draft',
    'transitional_two': 'Cannot Transition to blah blah'

}

def error_string(function):
    def wrapper(*args, **kwargs):
        valid = function(*args, **kwargs)
        if valid and type(valid) is bool:
            return (True, None)
        else:
            return (False, valid_errors[function.__name__])
    return wrapper

def transition_error_string(function):
    def wrapper(*args, **kwargs):
        valid = function(*args, **kwargs)
        if valid and type(valid) is bool:
            return (True, None)
        else:
            return (False, valid_errors['transitional_two'])
    return wrapper

def illegal_transition(agreement):
    return False

@error_string
def signed_date_valid(agreement):
    now = date.today()
    if agreement.signed_by_unicef_date > now or agreement.signed_by_partner_date > now:
        return False
    return True

@error_string
def transition_to_draft(agreement):
    return True if can_proceed(agreement.transition_to_draft) else False

class AgreementValid(object):

    # TODO: Django fsm gives us some sort of mapping like this
    transitions = [
        {
            'from':['active'],
            'to':['suspended'],
            'transition_function': 'transition_to_suspended'
        }
    ]

    def __init__(self, new, old, user):
        self.new = new
        self.old = old
        self.user = user

    @transition_error_string
    def check_transition(self, transition):
        if not transition:
            print 'no Transition'
            return True
        return can_proceed(transition)

    def get_transition(self):
        for obj in self.transitions:
            print obj
            print self.old.status
            print self.new.status
            print 'what'
            if self.old.status in obj['from']:
                if self.new.status in obj['to']:
                    return getattr(self.new, obj['transition_function'])
        return None

    @cached_property
    def transition(self):
        return self.get_transition()

    @cached_property
    def basic_validation(self):
        '''
        basic set of validations to make sure new state is correct
        :return: True or False
        '''
        # return signed_date_valid(self.new)
        return self.check_transition(self.transition)

    @property
    def is_valid(self):
        return self.basic_validation[0]

    @property
    def errors(self):
        return self.basic_validation[1]

