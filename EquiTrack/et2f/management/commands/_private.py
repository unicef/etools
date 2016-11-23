from django.db.models.query_utils import Q

from et2f import UserTypes, TripStatus
from et2f.models import TravelPermission


def make_permissions_for_model(user_type, status, model_name, fields):
    permissions = []

    for field_name, value in fields.items():
        name = '_'.join((user_type, status, model_name, field_name, TravelPermission.EDIT))
        kwargs = dict(name=name,
                      user_type=user_type,
                      status=status,
                      model=model_name,
                      field=field_name,
                      permission_type=TravelPermission.EDIT,
                      value=True)
        permissions.append(TravelPermission(**kwargs))

        name = '_'.join((user_type, status, model_name, field_name, TravelPermission.VIEW))
        kwargs = dict(name=name,
                      user_type=user_type,
                      status=status,
                      model=model_name,
                      field=field_name,
                      permission_type=TravelPermission.VIEW,
                      value=True)
        permissions.append(TravelPermission(**kwargs))
        if value is not None:
            permissions.extend(make_permissions_for_model(user_type, status, field_name, value))
    return permissions


def generate_all_permissions(command):
    command.stdout.write('Delting old permission matrix')
    TravelPermission.objects.all().delete()

    model_field_mapping = {'clearances': {'id': None,
                                          'medical_clearance': None,
                                          'security_clearance': None,
                                          'security_course': None},
                           'cost_assignments': {'id': None,
                                                'wbs': None,
                                                'share': None,
                                                'grant': None},
                           'deductions': {'id': None,
                                          'date': None,
                                          'breakfast': None,
                                          'lunch': None,
                                          'dinner': None,
                                          'accomodation': None,
                                          'no_dsa': None,
                                          'day_of_the_week': None},
                           'expenses': {'id': None,
                                        'type': None,
                                        'document_currency': None,
                                        'account_currency': None,
                                        'amount': None},
                           'itinerary': {'id': None,
                                         'origin': None,
                                         'destination': None,
                                         'departure_date': None,
                                         'arrival_date': None,
                                         'dsa_region': None,
                                         'overnight_travel': None,
                                         'mode_of_travel': None,
                                         'airlines': None},
                           'reference_number': None,
                           'supervisor': None,
                           'office': None,
                           'end_date': None,
                           'section': None,
                           'international_travel': None,
                           'traveler': None,
                           'start_date': None,
                           'ta_required': None,
                           'purpose': None,
                           'id': None,
                           'status': None,
                           'mode_of_travel': None,
                           'estimated_travel_cost': None,
                           'currency': None,
                           'cost_summary': None,
                           'activities': {'id': None,
                                          'travel_type': None,
                                          'partner': None,
                                          'partnership': None,
                                          'result': None,
                                          'locations': None,
                                          'primary_traveler': None,
                                          'date': None}}

    command.stdout.write('Regenerating permission matrix')
    new_permissions = []
    for user_type in UserTypes.CHOICES:
        for status in TripStatus.CHOICES:
            new_permissions.extend(make_permissions_for_model(user_type[0],
                                                              status[0],
                                                              'travel',
                                                              model_field_mapping))

    TravelPermission.objects.bulk_create(new_permissions)
    command.stdout.write('Permission matrix saved')


class PermissionMatrixSetter(object):
    def __init__(self, command):
        self._command = command

    def log(self, message):
        self._command.stdout.write(message)

    def set_up_all(self):
        self.set_up_god()
        self.set_up_anyone()
        self.set_up_traveler()
        self.set_up_travel_administrator()
        self.set_up_supervisor()
        self.set_up_travel_focal_point()
        self.set_up_finance_focal_point()
        self.set_up_representative()

    def revoke_edit(self, qs):
        num_revoked = qs.filter(permission_type=TravelPermission.EDIT).update(value=False)
        self.log('{} edit permissions revoked'.format(num_revoked))

    def grant_edit(self, qs):
        num_revoked = qs.filter(permission_type=TravelPermission.EDIT).update(value=True)
        self.log('{} edit permissions granted'.format(num_revoked))

    def revoke_view(self, qs):
        num_revoked = qs.filter(permission_type=TravelPermission.VIEW).update(value=False)
        self.log('{} view permissions revoked'.format(num_revoked))

    def get_related_q(self, fields):
        q = Q(model__in=fields)
        q |= Q(Q(model='travel') & Q(field__in=fields))
        return q

    def set_up_god(self):
        self.log('Set up permissions for god')
        TravelPermission.objects.filter(user_type=UserTypes.GOD).update(value=True)

    def set_up_anyone(self):
        self.log('Set up permissions for anyone')
        qs = TravelPermission.objects.filter(user_type=UserTypes.ANYONE)
        self.revoke_edit(qs)

        q = self.get_related_q(['deductions', 'expenses', 'cost_assignments', 'cost_summary'])
        sub_qs = qs.filter(q)
        self.revoke_view(sub_qs)
        self.revoke_edit(sub_qs)

        sub_qs = qs.filter(model='travel', field__in=['estimated_travel_cost', 'currency'])
        self.revoke_view(sub_qs)
        self.revoke_edit(sub_qs)

    def set_up_traveler(self):
        self.log('Set up permissions for travel traveler')
        qs = TravelPermission.objects.filter(user_type=UserTypes.TRAVELER)

        self.revoke_edit(qs.filter(model='travel', field='traveler'))
        status_where_hide = [TripStatus.PLANNED,
                             TripStatus.SUBMITTED,
                             TripStatus.APPROVED,
                             TripStatus.CANCELLED,
                             TripStatus.REJECTED]

        q = Q(status__in=status_where_hide) & self.get_related_q(['deductions', 'expenses'])
        sub_qs = qs.filter(q)
        self.revoke_view(sub_qs)
        self.revoke_edit(sub_qs)

        sub_qs = qs.filter(status__in=[TripStatus.SUBMITTED,
                                       TripStatus.CERTIFICATION_SUBMITTED,
                                       TripStatus.CERTIFICATION_REJECTED,
                                       TripStatus.CERTIFICATION_APPROVED,
                                       TripStatus.SENT_FOR_PAYMENT,
                                       TripStatus.COMPLETED])
        self.revoke_edit(sub_qs)

        sub_qs = qs.filter(self.get_related_q(['activities']), status__in=[TripStatus.SENT_FOR_PAYMENT,
                                                                           TripStatus.CERTIFICATION_REJECTED])
        self.grant_edit(sub_qs)

    def set_up_travel_administrator(self):
        self.log('Set up permissions for travel administrator')
        qs = TravelPermission.objects.filter(user_type=UserTypes.TRAVEL_ADMINISTRATOR)

        sub_qs = qs.filter(status=TripStatus.APPROVED).exclude(self.get_related_q(['activities']))
        self.revoke_edit(sub_qs)

        sub_qs = qs.filter(status__in=[TripStatus.SENT_FOR_PAYMENT,
                                      TripStatus.CERTIFICATION_REJECTED])
        sub_qs = sub_qs.exclude(self.get_related_q(['activities']))
        self.revoke_edit(sub_qs)

        sub_qs = qs.filter(status__in=[TripStatus.COMPLETED, TripStatus.CERTIFICATION_APPROVED])
        self.revoke_edit(sub_qs)

    def set_up_supervisor(self):
        self.log('Set up permissions for supervisor')
        qs = TravelPermission.objects.filter(user_type=UserTypes.SUPERVISOR)
        self.revoke_edit(qs)

    def set_up_travel_focal_point(self):
        self.log('Set up permissions for travel focal point')
        fields_to_edit = ['itinerary']
        status_where_edit = [TripStatus.PLANNED,
                             TripStatus.SUBMITTED,
                             TripStatus.CANCELLED,
                             TripStatus.APPROVED,
                             TripStatus.REJECTED]
        qs = TravelPermission.objects.filter(user_type=UserTypes.TRAVEL_FOCAL_POINT)
        self.revoke_edit(qs)

        q = Q(status__in=status_where_edit) & self.get_related_q(fields_to_edit)
        num_granted = qs.filter(q).update(value=True)
        self.log('{} permissions granted'.format(num_granted))

        sub_qs = qs.filter(model='travel', field__in=['estimated_travel_cost', 'currency'])
        sub_qs = sub_qs.exclude(status__in=[TripStatus.COMPLETED,
                                            TripStatus.CERTIFICATION_SUBMITTED,
                                            TripStatus.CERTIFICATION_APPROVED,
                                            TripStatus.CERTIFICATION_REJECTED])
        self.grant_edit(sub_qs)

    def set_up_finance_focal_point(self):
        self.log('Set up permissions for finance focal point')
        fields_to_edit = ['itinerary', 'deductions', 'expenses', 'cost_assignments']
        status_where_edit = [TripStatus.PLANNED,
                             TripStatus.SUBMITTED,
                             TripStatus.CANCELLED,
                             TripStatus.APPROVED,
                             TripStatus.REJECTED,
                             TripStatus.CERTIFICATION_APPROVED,
                             TripStatus.SENT_FOR_PAYMENT]
        qs = TravelPermission.objects.filter(user_type=UserTypes.FINANCE_FOCAL_POINT)
        self.revoke_edit(qs)

        q = Q(status__in=status_where_edit) & self.get_related_q(fields_to_edit)
        sub_qs = qs.filter(q)
        self.grant_edit(sub_qs)

        sub_qs = qs.filter(model='travel', field__in=['estimated_travel_cost', 'currency']).exclude(
            status__in=[TripStatus.COMPLETED,
                        TripStatus.CERTIFICATION_SUBMITTED,
                        TripStatus.CERTIFICATION_APPROVED,
                        TripStatus.CERTIFICATION_REJECTED])
        self.grant_edit(sub_qs)

    def set_up_representative(self):
        qs = TravelPermission.objects.filter(user_type=UserTypes.REPRESENTATIVE)
        self.revoke_edit(qs)


def populate_permission_matrix(command):
    generate_all_permissions(command)
    PermissionMatrixSetter(command).set_up_all()
