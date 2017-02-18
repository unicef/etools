from EquiTrack.validation_mixins import CompleteValidation, check_rigid_fields
from reports.models import ResultType


def check_if_year_correct(year):
    try:
        y = int(year)
        return 1980 < y < 2030
    except Exception as e:
        return False
    return True


def cp_output_valid(r):
    if not r.result:
        return False
    elif r.result.result_type.name != ResultType.OUTPUT:
        return False
    return True

def year_valid(r):
    if not r.year:
        return False
    elif not check_if_year_correct(r.year):
        return False
    return True

def planned_amount_valid(r):
    if not r.planned_amount:
        return False
    return True



class GovernmentInterventionResultValid(CompleteValidation):

    VALIDATION_CLASS = 'partners.GovernmentInterventionResult'
    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [
        cp_output_valid,
        year_valid,
        planned_amount_valid
    ]

    VALID_ERRORS = {
        'cp_output_valid': 'Invalid CP Output, please select an Output as your CP Output',
        'year_valid': 'Invalid Year, please select a valid year',
        'planned_amount_valid': 'Please fill in Planned Cash Transfers'
    }
