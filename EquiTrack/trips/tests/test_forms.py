__author__ = 'unicef-leb-inn'

from datetime import timedelta, datetime
from django.db.models.fields.related import ManyToManyField

from tenant_schemas.test.cases import TenantTestCase

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


class TestTripForm(TenantTestCase):

    def setUp(self):
        self.trip = TripFactory(
            owner__first_name='Fred',
            owner__last_name='Test',
            purpose_of_travel='To test some trips'
        )

    def test_form_validation_for_programme_monitoring(self):
        trip_dict = to_dict(self.trip)
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0],
                         "You must select the interventions related to this trip or change the Travel Type")

    def test_form_validation_for_international_travel(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['international_travel'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0],
                         "You must select the Representative for international travel trips")

    def test_form_validation_for_bigger_date(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['from_date'] = trip_dict['from_date'] + timedelta(days=3)
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['to_date'], [u'The to date must be greater than the from date'])

    def test_form_validation_for_past_trip(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['from_date'] = trip_dict['from_date'] - timedelta(days=3)
        trip_dict['to_date'] = trip_dict['to_date'] - timedelta(days=2)
        trip_dict['status'] = u'submitted'
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0],
                         'This trip\'s dates happened in the past and therefore cannot be submitted')

    def test_form_validation_for_owner_is_supervisor(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['supervisor'] = trip_dict['owner']
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0], 'You can\'t supervise your own trips')

    def test_form_validation_for_status_approved(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['status'] = u'approved'
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0], 'Only the supervisor can approve this trip')

    def test_form_validation_for_ta_required(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['ta_required'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0],
                         'This trip needs a programme assistant to create a Travel Authorisation (TA)')

    def test_form_validation_for_approved_by_supervisor(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['approved_by_supervisor'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0], 'Please put the date the supervisor approved this Trip')

    def test_form_validation_for_approved_by_budget_owner(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['approved_by_budget_owner'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0], 'Please put the date the budget owner approved this Trip')

    def test_form_validation_for_ta_drafted_vision(self):
        self.trip.status = Trip.APPROVED
        self.trip.approved_by_supervisor = True
        self.trip.approved_date = datetime.today()
        self.trip.date_supervisor_approved = datetime.today()
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['ta_drafted'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0], 'For TA Drafted trip you must select a Vision Approver')

    def test_form_validation_for_completed_no_report(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['status'] = u'completed'
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0],
                         'You must provide a narrative report before the trip can be completed')

    def test_form_validation_for_completed_no_report_staff_entl(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'staff_entitlement'
        trip_dict['status'] = u'completed'
        form = TripForm(data=trip_dict)
        self.assertTrue(form.is_valid())

    # def test_form_validation_for_completed_ta_required(self):
    #     trip_dict = to_dict(self.trip)
    #     trip_dict['travel_type'] = u'advocacy'
    #     trip_dict['status'] = u'completed'
    #     trip_dict['programme_assistant'] = UserFactory().id
    #     trip_dict['ta_required'] = True
    #     trip_dict['pending_ta_amendment'] = True
    #     trip_dict['main_observations'] = 'Test'
    #     form = TripForm(data=trip_dict)
    #     self.assertFalse(form.is_valid())
    #     self.assertEqual(form.non_field_errors()[0],
    #                      'Due to trip having a pending amendment to the TA, '
    #                      ' only the travel focal point can complete the trip')


    # def test_form_validation_for_staff_development(self):
    #     trip_dict = to_dict(self.trip)
    #     trip_dict['travel_type'] = u'staff_development'
    #     trip_dict['status'] = u'completed'
    #     trip_dict['main_observations'] = u'Testing completed'
    #     form = TripForm(data=trip_dict)
    #     self.assertFalse(form.is_valid())
    #     self.assertEqual(form.non_field_errors()[0],
    #                      'STAFF DEVELOPMENT trip must be certified by Human '
    #                      'Resources before it can be completed')

    def test_form_validation_for_date_greater(self):
        form = TravelRoutesForm(data={'trip': self.trip.id,
                                      'origin': 'Test1',
                                      'destination': 'Test2',
                                      'depart': datetime.now() + timedelta(hours=3),
                                      'arrive': datetime.now()})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0], 'Arrival must be greater than departure')

    def test_form_validation_for_no_trip_location(self):
        trip_dict = to_dict(self.trip)
        trip_dict['status'] = u'submitted'
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
