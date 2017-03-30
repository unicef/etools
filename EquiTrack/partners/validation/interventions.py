import logging
from datetime import date, datetime

from EquiTrack.validation_mixins import TransitionError, CompleteValidation, check_rigid_fields, StateValidError

def partnership_manager_only(i, user):
    # Transition cannot happen by a user that';s not a Partnership Manager
    if not user.groups.filter(name__in=['Partnership Manager']).count():
        raise TransitionError(['Only Partnership Managers can execute this transition'])
    return True

def transition_ok(i):
    return True

def transition_to_active(i):
    today = date.today()
    errors = []
    if not i.signed_by_unicef_date:
        errors.append({'signed_by_unicef_date': ['This field is required. Transition to active illegal.']})
    if not i.unicef_signatory:
        errors.append({'unicef_signatory': ['This field is required. Transition to active illegal.']})
    if not i.signed_by_partner_date:
        errors.append({'signed_by_partner_date': ['This field is required. Transition to active illegal.']})
    if not i.partner_authorized_officer_signatory:
        errors.append({'partner_authorized_officer_signatory': ['This field is required. Transition to active illegal.']})
    if not i.start:
        errors.append({'start': ['This field is required. Transition to active illegal.']})
    if not i.end:
        errors.append({'end': ['This field is required. Transition to active illegal.']})
    if not i.start <= today:
        errors.append({'start': ['Cannot be in the future. Transition to active illegal.']})
    if not i.end > today:
        errors.append({'end': ['Cannot be in the past. Transition to active illegal.']})
    if not partner_focal_points_valid(i):
        errors.append({'partner_focal_points': ['Partner focal point is required if Intervention status is ACTIVE or IMPLEMENTED.']})
    if not unicef_focal_points_valid(i):
        errors.append({'unicef_focal_points': ['Unicef focal point is required if Intervention status is ACTIVE or IMPLEMENTED.']})
    if not population_focus_valid(i):
        errors.append({'population_focus': ['Population focus is required if Intervention status is ACTIVE or IMPLEMENTED.']})
    # Planned budget fields
    if not i.planned_budget.exists():
        errors.append({'planned_budget': ['Planned budget is required if Intervention status is ACTIVE or IMPLEMENTED.']})
    for budget in i.planned_budget.all():
        if not unicef_cash_valid(budget):
            errors.append({
                'planned_budget': {
                    'unicef_cash': ['Unicef cash is required if Intervention status is ACTIVE or IMPLEMENTED.'],
                }
            })
        if not partner_contribution_valid(budget):
            errors.append({
                'planned_budget': {
                    'partner_contribution': ['Partner contrubution is required if Intervention status is ACTIVE or IMPLEMENTED.'],
                }
            })
    # Sector locations field
    if not i.sector_locations.exists():
        errors.append({'sector_locations': ['Sector locations are required if Intervention status is ACTIVE or IMPLEMENTED.']})
    for sectorlocation in i.sector_locations.all():
        if not sector_location_valid(sectorlocation):
            errors.append({'sector_locations': ['Sector and locations are required if Intervention status is ACTIVE or IMPLEMENTED.']})

    if errors:
        raise TransitionError(errors)

    return True

def transition_to_implemented(i):
    today = date.today()
    errors = []
    if not i.end < today:
        errors.append({'end': ['End date has not passed. Transition to ended illegal.']})
    if not partner_focal_points_valid(i):
        errors.append({'partner_focal_points': ['Partner focal point is required if Intervention status is ACTIVE or IMPLEMENTED.']})
    if not unicef_focal_points_valid(i):
        errors.append({'unicef_focal_points': ['Unicef focal point is required if Intervention status is ACTIVE or IMPLEMENTED.']})
    if not population_focus_valid(i):
        errors.append({'population_focus': ['Population focus is required if Intervention status is ACTIVE or IMPLEMENTED.']})
    # Planned budget fields
    if not i.planned_budget.exists():
        errors.append({'planned_budget': ['Planned budget is required if Intervention status is ACTIVE or IMPLEMENTED.']})
    for budget in i.planned_budget.all():
        if not unicef_cash_valid(budget):
            errors.append({
                'planned_budget': {
                    'unicef_cash': ['Unicef cash is required if Intervention status is ACTIVE or IMPLEMENTED.'],
                }
            })
        if not partner_contribution_valid(budget):
            errors.append({
                'planned_budget': {
                    'partner_contribution': ['Partner contrubution is required if Intervention status is ACTIVE or IMPLEMENTED.'],
                }
            })
    # Sector locations field
    if not i.sector_locations.exists():
        errors.append({'sector_locations': ['Sector locations are required if Intervention status is ACTIVE or IMPLEMENTED.']})
    for sectorlocation in i.sector_locations.all():
        if not sector_location_valid(sectorlocation):
            errors.append({'sector_locations': ['Sector and locations are required if Intervention status is ACTIVE or IMPLEMENTED.']})

    if errors:
        raise TransitionError(errors)

    return True

def start_end_dates_valid(i):
    if i.start and i.end and \
            i.end < i.start:
        return False
    return True

def partner_authorized_officer_signatory_valid(i):
    today = date.today()
    if i.signed_by_partner_date and not i.partner_authorized_officer_signatory:
        return False
    return True

def unicef_signatory_valid(i):
    today = date.today()
    if i.signed_by_unicef_date and not i.unicef_signatory:
        return False
    return True

def signed_by_unicef_date_valid(i):
    today = date.today()
    if i.signed_by_unicef_date and i.signed_by_unicef_date > today:
        return False
    return True

def signed_by_partner_date_valid(i):
    today = date.today()
    if i.signed_by_partner_date and i.signed_by_partner_date > today:
        return False
    return True

def document_type_pca_valid(i):
    if i.agreement.agreement_type == "PCA" and i.document_type not in ["PD", "SHPD"]:
        return False
    return True

def document_type_ssfa_valid(i):
    if i.agreement.agreement_type == "SSFA" and i.document_type not in ["SSFA"]:
        return False
    return True

def partner_focal_points_valid(i):
    if not i.partner_focal_points:
        return False
    return True

def unicef_focal_points_valid(i):
    if not i.unicef_focal_points:
        return False
    return True

def population_focus_valid(i):
    if not i.population_focus:
        return False
    return True

def unicef_cash_valid(b):
    if not b.unicef_cash:
        return False
    return True

def partner_contribution_valid(b):
    if not b.partner_contribution:
        return False
    return True

def sector_location_valid(sl):
    if not sl.sector or not sl.locations.exists():
        return False
    return True

def amendments_valid(i):
    for a in i.amendments.all():
        if not a.type or not a.signed_date:
            return False
    return True


class InterventionValid(CompleteValidation):

    # TODO: add user on basic and state

    VALIDATION_CLASS = 'partners.Intervention'
    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [
        start_end_dates_valid,
        partner_authorized_officer_signatory_valid,
        unicef_signatory_valid,
        signed_by_partner_date_valid,
        signed_by_unicef_date_valid,
        document_type_pca_valid,
        document_type_ssfa_valid,
        amendments_valid,
    ]

    VALID_ERRORS = {
        'suspended_expired_error': {
            'status': ['State suspended cannot be modified since the end date of the intervention surpasses today']
        },
        'start_end_dates_valid': {
            'start': ['Start date must precede end date']
        },
        'partner_authorized_officer_signatory_valid': {
            'partner_authorized_officer_signatory': ['This field is required.'],
        },
        'unicef_signatory_valid': {
            'unicef_signatory': ['This field is required.'],
        },
        'signed_by_partner_date_valid': {
            'signed_by_partner_date': ['Signatures cannot be dated in the future.'],
        },
        'signed_by_unicef_date_valid': {
            'signed_by_unicef_date': ['Signatures cannot be dated in the future.'],
        },
        'document_type_pca_valid': {
            'document_type': ['Document type must be PD or SHPD in case of agreement is PCA.']
        },
        'document_type_ssfa_valid': {
            'document_type': ['Document type must be SSFA in case of agreement is SSFA.']
        },
        'amendments_valid': {
            'amendments' : {
                'type': ['This field is required.'],
                'signed_date': ['This field is required.'],
                'signed_amendment': ['This field is required.'],
            }
        }
    }

    def state_suspended_valid(self, intervention, user=None):
        # if we're just now trying to transition to suspended
        if intervention.old_instance and intervention.old_instance.status == intervention.status:
            #TODO ask business owner what to do if a suspended intervention passes end date and is being modified
            if intervention.end > date.today():
                raise StateValidError(['suspended_expired_error'])

        return True

    def state_active_valid(self, intervention, user=None):
        # Intervention fields
        # TODO: reinstate after business owners ok
        # if intervention.old_instance and intervention.old_instance.status == intervention.status:
        #     validate_rigid_budget = True
        #     rigid_fields = [
        #         'signed_by_unicef_date',
        #         'signed_by_partner_date',
        #     ]
        #     rigid_valid, field = check_rigid_fields(intervention, rigid_fields)
        #     if not rigid_valid:
        #         raise StateValidError(['Cannot change fields while intervention is active: {}'.format(field)])
        #
        #     # Planned budget fields
        #     planned_budget_rigid_fields = [
        #         'unicef_cash',
        #         'partner_contribution',
        #         'in_kind_amount',
        #         'unicef_cash_local',
        #         'partner_contribution_local',
        #         'in_kind_amount_local',
        #     ]
        #     for amd in intervention.amendments.filter():
        #         if amd.type in [amd.CTBGT20, amd.CTBLT20, amd.CABLT20, amd.CABGT20, amd.CABGT20FACE]:
        #             validate_rigid_budget = False
        #             break
        #     if validate_rigid_budget:
        #         # avoid n*m list traversal with dict lookup
        #         old_instance_dict = {x.id: x for x in intervention.old_instance.planned_budget_old}
        #         for budget in intervention.planned_budget.filter():
        #             old_instance = old_instance_dict.get(budget.id)
        #             planned_budget_rigid_valid, field = check_rigid_fields(budget, planned_budget_rigid_fields, old_instance)
        #             if not planned_budget_rigid_valid:
        #                 raise StateValidError(['Cannot change fields while intervention is active: {}'.format(field)])
        #
        #     # Planned visits fields
        #     planned_visits_rigid_fields = [
        #         'programmatic',
        #         'spot_checks',
        #         'audit',
        #     ]
        #
        #     # avoid n*m list traversal with dict lookup
        #     old_instance_dict = {x.id: x for x in intervention.old_instance.planned_visits_old}
        #     for visit in intervention.planned_visits.filter():
        #         old_instance = old_instance_dict.get(visit.id)
        #         planned_visits_rigid_valid, field = check_rigid_fields(visit, planned_visits_rigid_fields, old_instance)
        #         if not planned_visits_rigid_valid:
        #             raise StateValidError(['Cannot change fields while intervention is active: {}'.format(field)])

        return True
