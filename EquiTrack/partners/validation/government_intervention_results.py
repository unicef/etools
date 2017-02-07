from EquiTrack.validation_mixins import CompleteValidation, check_rigid_fields


def planned_amount_valid(r):
    if r.old_instance:
        valid, _ = check_rigid_fields(r, ["planned_amount"])
        return valid
    return True

def planned_visits_valid(r):
    if r.old_instance:
        valid, _ = check_rigid_fields(r, ["planned_visits"])
        return valid
    return True

def activity_valid(r):
    for k, v in r.activity.items():
        if not v:
            return False
    return True

def sectors_valid(r):
    if not r.sectors.exists():
        return False
    return True

def sections_valid(r):
    # TODO Figure out how to create Section on test schema
    # if not r.sections.exists():
    #     return False
    return True


class GovernmentInterventionResultValid(CompleteValidation):

    VALIDATION_CLASS = 'partners.GovernmentInterventionResult'
    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [
        planned_amount_valid,
        planned_visits_valid,
        activity_valid,
        sectors_valid,
        sections_valid,
    ]

    VALID_ERRORS = {
        'planned_amount_valid': 'Planned amount cannot be changed.',
        'planned_visits_valid': 'Planned visits cannot be changed.',
        'activity_valid': 'Both ID and Description is needed for activity.',
        'sectors_valid': 'Sector is required.',
        'sections_valid': 'Section is required.',
    }
