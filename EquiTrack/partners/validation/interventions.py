from datetime import date
import logging

from EquiTrack.validation_mixins import TransitionError, CompleteValidation, StateValidError, check_rigid_related

logger = logging.getLogger('partners.interventions.validation')

def partnership_manager_only(i, user):
    # Transition cannot happen by a user that';s not a Partnership Manager
    if not user.groups.filter(name__in=['Partnership Manager']).count():
        raise TransitionError(['Only Partnership Managers can execute this transition'])
    return True


def transition_ok(i):
    return True


def transition_to_active(i):
    # i = intervention
    # TODO: validation update
    # if not (i.signed_by_unicef_date and i.unicef_signatory and i.signed_by_partner_date and
    #         i.partner_authorized_officer_signatory and i.start and i.end):
    #     raise TransitionError(['Transition to active illegal: signatories and dates required'])
    # today = date.today()
    # if not i.start <= today and i.end > today:
    #     raise TransitionError(['Transition to active illegal: not within the date range'])
    # if not partner_focal_points_valid(i):
    #     raise TransitionError(['Partner focal point is required if Intervention status is ACTIVE or IMPLEMENTED.'])
    # if not unicef_focal_points_valid(i):
    #     raise TransitionError(['Unicef focal point is required if Intervention status is ACTIVE or IMPLEMENTED.'])
    # # Planned budget fields
    # if not i.planned_budget:
    #     raise TransitionError(['Planned budget is required if Intervention status is ACTIVE or IMPLEMENTED.'])
    # for budget in i.planned_budget.all():
    #     if not unicef_cash_valid(budget):
    #         raise TransitionError(['Unicef cash is required if Intervention status is ACTIVE or IMPLEMENTED.'])
    #     if not partner_contribution_valid(budget):
    #         raise TransitionError(['Partner contrubution is required if Intervention status is ACTIVE or IMPLEMENTED.'])
    # # Sector locations field
    # if not i.sector_locations.exists():
    #     raise TransitionError(['Sector locations are required if Intervention status is ACTIVE or IMPLEMENTED.'])
    # for sectorlocation in i.sector_locations.all():
    #     if not sector_location_valid(sectorlocation):
    #         raise TransitionError(
    #             ['Sector and locations are required if Intervention status is ACTIVE or IMPLEMENTED.'])

    return True


def transition_to_implemented(i):
    # i = intervention
    # TODO: validation update
    # today = date.today()
    # if not i.end < today:
    #     raise TransitionError(['Transition to ended illegal: end date has not passed'])
    # if not partner_focal_points_valid(i):
    #     raise TransitionError(['Partner focal point is required if Intervention status is ACTIVE or IMPLEMENTED.'])
    # if not unicef_focal_points_valid(i):
    #     raise TransitionError(['Unicef focal point is required if Intervention status is ACTIVE or IMPLEMENTED.'])
    # # Planned budget fields
    # if not i.planned_budget.exists():
    #     raise TransitionError(['Planned budget is required if Intervention status is ACTIVE or IMPLEMENTED.'])
    # for budget in i.planned_budget.all():
    #     if not unicef_cash_valid(budget):
    #         raise TransitionError(['Unicef cash is required if Intervention status is ACTIVE or IMPLEMENTED.'])
    #     if not partner_contribution_valid(budget):
    #         raise TransitionError(['Partner contrubution is required if Intervention status is ACTIVE or IMPLEMENTED.'])
    # Sector locations field
    if not i.sector_locations.exists():
        raise TransitionError(['Sector locations are required if Intervention status is ACTIVE or IMPLEMENTED.'])
    for sectorlocation in i.sector_locations.all():
        if not sector_location_valid(sectorlocation):
            raise TransitionError(
                ['Sector and locations are required if Intervention status is ACTIVE or IMPLEMENTED.'])
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

    logger.warn('add this validation once statuses are fixed')
    # TODO: pmp-redesign add this validation
    # if i.status not in [i.ACTIVE, i.SIGNED] and i.amendments.exists():
    if i.status not in [i.ACTIVE] and i.amendments.exists():
        # this prevents any changes in amendments if the status is not in Signed or Active
        if not check_rigid_related(i, 'amendments'):
            return False


    for a in i.amendments.all():
        if a.OTHER in a.types and a.other_description is None:
            return False
        if not a.signed_date:
            return False
    return True


class InterventionValid(CompleteValidation):

    # TODO: add user on basic and state

    VALIDATION_CLASS = 'partners.Intervention'
    # validations that will be checked on every object... these functions only take the new instance
    BASIC_VALIDATIONS = [
        start_end_dates_valid,
        signed_date_valid,
        document_type_pca_valid,
        document_type_ssfa_valid,
        amendments_valid,
    ]

    VALID_ERRORS = {
        'suspended_expired_error': 'State suspended cannot be modified since the end date of the intervention surpasses today',
        'start_end_dates_valid': 'Start date must precede end date',
        'signed_date_valid': 'Unicef signatory and partner signatory as well as dates required, signatures cannot be dated in the future',
        'document_type_pca_valid': 'Document type must be PD or SHPD in case of agreement is PCA.',
        'document_type_ssfa_valid': 'Document type must be SSFA in case of agreement is SSFA.',
        'amendments_valid': 'Type, signed date, and signed amendment are required in Amendments.',
    }

    def state_suspended_valid(self, intervention, user=None):
        # if we're just now trying to transition to suspended
        if intervention.old_instance and intervention.old_instance.status == intervention.status:
            # TODO ask business owner what to do if a suspended intervention passes end date and is being modified
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
