
import logging
from datetime import date, datetime

from EquiTrack.validation_mixins import TransitionError, CompleteValidation, check_rigid_fields, StateValidError


class GovernmentInterventionValid(CompleteValidation):

    # TODO: add user on basic and state
    # TODO add validations
    VALIDATION_CLASS = 'partners.GovernmentIntervention'
    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = []

    VALID_ERRORS = {
    }