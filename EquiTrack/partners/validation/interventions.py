import logging
from datetime import date, datetime

from EquiTrack.validation_mixins import TransitionError, CompleteValidation, check_rigid_fields, StateValidError


def transition_to_active(i):
    # i = intervention
    if not (i.signed_by_unicef_date and i.unicef_signatory and i.signed_by_partner_date and
            i.partner_authorized_officer_signatory):
        raise TransitionError(['Transition to active illegal: signatories and dates required'])
    today = date.today()
    if not i.start < today and i.end > today:
        raise TransitionError(['Transition to active illegal: not within the date range'])
    return True

def transition_to_implemented(i):
    # i = intervention
    today = date.today()
    if not i.end < today:
        raise TransitionError(['Transition to ended illegal: end date has not passed'])
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

class InterventionValid(CompleteValidation):

    # TODO: add user on basic and state

    VALIDATION_CLASS = 'partners.Intervention'
    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [start_end_dates_valid, signed_date_valid]

    VALID_ERRORS = {
        'suspended_expired_error': 'State suspended cannot be modified since the end date of the intervention surpasses today',
        'start_end_dates_valid': 'check the start and end dates',
        'signed_date_valid': 'Unicef signatory and partner signatory as well as dates required, signatures cannot be dated in the future'
    }

    def state_suspended_valid(self, intervention, user=None):
        # if we're just now trying to transition to suspended
        if intervention.old_instance and intervention.old_instance.status == intervention.status:
            #TODO ask business owner what to do if a suspended intervention passes end date and is being modified
            if intervention.end > date.today():
                raise StateValidError(['suspeded_expired_error'])

        return True

    def state_active_valid(self, intervention, user=None):
        # if we're just now trying to transition to suspended
        print 'state_active_called'
        rigid_fields = ['signed_by_unicef_date', 'signed_by_partner_date']
        rigid_valid, field = check_rigid_fields(intervention, rigid_fields)
        if not rigid_valid:
            raise StateValidError(['Cannot change fields while agreement is active: {}'.format(field)])
        return True

