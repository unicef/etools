__author__ = 'unicef-leb-inn'

from datetime import timedelta, datetime
from django.db.models.fields.related import ManyToManyField

from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase

from EquiTrack.factories import TripFactory, UserFactory, PartnershipFactory
from trips.forms import TripForm, TravelRoutesForm
from trips.models import Trip


def to_dict(instance):
    opts = instance._meta
    data = {}
    for f in opts.concrete_fields + opts.many_to_many:
        if isinstance(f, ManyToManyField):
            if instance.pk is None:
                data[f.name] = []
            else:
                data[f.name] = list(f.value_from_object(instance).values_list('pk', flat=True))
        else:
            data[f.name] = f.value_from_object(instance)
    return data


class SimpleObject(object):
    pass


class TestTripForm(TenantTestCase):

    def setUp(self):
        self.trip = TripFactory(
            status=Trip.PLANNED,
            owner__first_name='Fred',
            owner__last_name='Test',
            supervisor__first_name='SupervisorJohn',
            supervisor__last_name='SupervisorDoe',
            purpose_of_travel='To test some trips',
        )

    def create_form(self, data=None, instance=None, user=None):
        trip_dict = to_dict(self.trip)
        if data:
            for k, v in data.iteritems():
                trip_dict[k] = v

        instance = instance if instance else self.trip
        form = TripForm(data=trip_dict, instance=instance)

        form.request = SimpleObject()
        form.request.user = user if user else self.trip.owner
        return form

    # def test_form_validation_for_programme_monitoring(self):
    #     form = self.create_form()
    #     self.assertFalse(form.is_valid())
    #     self.assertEqual(
    #         form.errors['pcas'][0],
    #         TripForm.ERROR_MESSAGES['no_linked_interventions']
    #     )

    def test_form_validation_for_international_travel(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = Trip.ADVOCACY
        trip_dict['international_travel'] = True
        form = self.create_form(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['representative'][0],
            TripForm.ERROR_MESSAGES['no_rep_for_int_travel']
        )

    def test_form_validation_for_bigger_date(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = Trip.ADVOCACY
        trip_dict['from_date'] = trip_dict['from_date'] + timedelta(days=3)
        form = self.create_form(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['to_date'][0],
            TripForm.ERROR_MESSAGES['to_date_less_than_from']
        )

    def test_form_validation_for_past_trip(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = Trip.ADVOCACY
        trip_dict['from_date'] = trip_dict['from_date'] - timedelta(days=3)
        trip_dict['to_date'] = trip_dict['to_date'] - timedelta(days=2)
        trip_dict['status'] = Trip.SUBMITTED
        form = self.create_form(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['to_date'][0],
            TripForm.ERROR_MESSAGES['trip_submitted_in_past']
        )

    def test_form_validation_for_owner_is_supervisor(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = Trip.ADVOCACY
        trip_dict['supervisor'] = trip_dict['owner']
        form = self.create_form(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['owner'][0],
            TripForm.ERROR_MESSAGES['owner_is_supervisor']
        )

    def test_form_validation_for_status_approved(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = Trip.ADVOCACY
        trip_dict['approved_by_supervisor'] = True
        trip_dict['date_supervisor_approved'] = datetime.today().date()
        form = self.create_form(data=trip_dict, user=self.trip.owner)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['approved_by_supervisor'][0],
            TripForm.ERROR_MESSAGES['not_approved_by_supervisor']
        )

    def test_form_validation_for_ta_required(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = Trip.ADVOCACY
        trip_dict['ta_required'] = True
        form = self.create_form(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['programme_assistant'][0],
            TripForm.ERROR_MESSAGES['no_assistant_for_TA']
        )

    def test_form_validation_for_approved_by_supervisor(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = Trip.ADVOCACY
        trip_dict['approved_by_supervisor'] = True
        form = self.create_form(data=trip_dict, user=self.trip.supervisor)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['date_supervisor_approved'][0],
            TripForm.ERROR_MESSAGES['no_date_supervisor_approve']
        )

    def test_form_validation_for_approved_by_budget_owner(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = Trip.ADVOCACY
        trip_dict['approved_by_budget_owner'] = True
        form = self.create_form(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['date_budget_owner_approved'][0],
            TripForm.ERROR_MESSAGES['no_date_budget_owner_approve']
        )

    def test_form_validation_for_manual_approval(self):
        self.trip.status = Trip.SUBMITTED
        self.trip.travel_type = Trip.ADVOCACY
        self.trip.ta_drafted = True
        self.trip.approved_by_supervisor = True
        self.trip.approved_date = datetime.today().date()
        self.trip.date_supervisor_approved = datetime.today().date()
        self.trip.save()

        trip_updates = {
            'status': Trip.APPROVED
        }
        form = self.create_form(data=trip_updates)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['status'][0],
            TripForm.ERROR_MESSAGES['cant_manually_approve']
        )

    def test_form_validation_for_completed_no_report(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['status'] = u'completed'
        form = self.create_form(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors()[0],
            TripForm.ERROR_MESSAGES['no_trip_report']
        )

    def test_form_validation_for_completed_no_report_staff_entl(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = Trip.STAFF_ENTITLEMENT
        trip_dict['status'] = Trip.COMPLETED
        form = self.create_form(data=trip_dict)
        self.assertTrue(form.is_valid())

    def test_form_validation_for_date_greater(self):
        form = TravelRoutesForm(
            data={'trip': self.trip.id,
                  'origin': 'Test1',
                  'destination': 'Test2',
                  'depart': datetime.now() + timedelta(hours=3),
                  'arrive': datetime.now()})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors()[0],
            'Arrival must be greater than departure'
        )

    # def test_form_validation_for_no_trip_location(self):
    #     trip_dict = to_dict(self.trip)
    #     trip_dict['status'] = Trip.SUBMITTED
    #     form = self.create_form(data=trip_dict)
    #     self.assertFalse(form.is_valid())
