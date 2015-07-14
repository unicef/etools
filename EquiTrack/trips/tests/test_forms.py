__author__ = 'unicef-leb-inn'
from datetime import timedelta, datetime

from django.test import TestCase
from django.db.models.fields.related import ManyToManyField

from EquiTrack.factories import TripFactory, UserFactory
from trips.forms import TripForm, TravelRoutesForm


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


class TestTripForm(TestCase):

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
        self.assertEqual(form.non_field_errors(),
                         ["You must select the PCAs related to this trip or change the Travel Type"])

    def test_form_validation_for_international_travel(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['international_travel'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(),
                         ["You must select the Representative for international travel trips"])

    def test_form_validation_for_bigger_date(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['from_date'] = trip_dict['from_date'] + timedelta(days=3)
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ['The to date must be greater than the from date'])

    def test_form_validation_for_owner_is_supervisor(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['supervisor'] = trip_dict['owner']
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ['You can\'t supervise your own trips'])

    def test_form_validation_for_ta_required(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['ta_required'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(),
                         ['This trip needs a programme assistant to create a Travel Authorisation (TA)'])

    def test_form_validation_for_approved_by_supervisor(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['approved_by_supervisor'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ['Please put the date the supervisor approved this Trip'])

    def test_form_validation_for_approved_by_budget_owner(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['approved_by_budget_owner'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ['Please put the date the budget owner approved this Trip'])

    def test_form_validation_for_status_approved(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['status'] = u'approved'
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ['Only the supervisor can approve this trip'])

    def test_form_validation_for_ta_drafted_vision(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['status'] = u'approved'
        trip_dict['ta_drafted'] = True
        trip_dict['approved_by_supervisor'] = True
        trip_dict['date_supervisor_approved'] = datetime.today()
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ['For TA Drafted trip you must select a Vision Approver'])



    def test_form_validation_for_completed_no_report(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['status'] = u'completed'
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(),
                         ['You must provide a narrative report before the trip can be completed'])

    def test_form_validation_for_staff_development(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'staff_development'
        trip_dict['status'] = u'completed'
        trip_dict['main_observations'] = u'Testing completed'
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(),
                                ['STAFF DEVELOPMENT trip must be certified by Human '
                                 'Resources before it can be completed'])

    def test_form_validation_for_date_greater(self):
        form = TravelRoutesForm(data={'origin': 'Test',
                                      'destination': 'Test',
                                      'depart': datetime.now() + timedelta(hours=3),
                                      'arrive': datetime.now()})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ['Arrival must be greater than departure'])

    # def test_form_validation_for_dates(self):
    #     form = TravelRoutesForm(data={'origin': 'Test',
    #                                   'destination': 'Test',
    #                                   'depart': datetime.now() + timedelta(hours=3),
    #                                   'arrive': datetime.now() + timedelta(days=3)})
    #     self.assertFalse(form.is_valid())
    #     self.assertEqual(form.non_field_errors(), ['Arrival must be greater than departure'])