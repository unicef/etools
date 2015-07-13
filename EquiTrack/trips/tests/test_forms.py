__author__ = 'unicef-leb-inn'
from datetime import timedelta, datetime

from django.test import TestCase
from django.db.models.fields.related import ManyToManyField
from django.core.exceptions import ValidationError

from EquiTrack.factories import TripFactory
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
        self.assertRaises(ValidationError("The to date must be greater than the from date"), form.clean())
        # self.assertRaisesMessage(ValidationError,
        #                          [u'The to date must be greater than the from date'],
        #                          form.clean())
        # self.assertRaisesRegexp(ValidationError,
        #                         "You must select the PCAs related to this trip or change the Travel Type")
        # self.assertEqual(form.errors['travel_type'], ["You must select the PCAs related to this trip or change the Travel Type"])

    def test_form_validation_for_bigger_date(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['from_date'] = trip_dict['from_date'] + timedelta(days=3)
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertRaisesMessage(ValidationError, u'The to date must be greater than the from date', form.clean())

    def test_form_validation_for_owner_is_supervisor(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['supervisor'] = trip_dict['owner']
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertRaisesRegexp(ValidationError, 'You can\'t supervise your own trips', form.is_valid())

    def test_form_validation_for_ta_required(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['ta_required'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertRaisesRegexp(ValidationError,
                                'This trip needs a programme assistant to create a Travel Authorisation (TA)')

    def test_form_validation_for_approved_by_supervisor(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['approved_by_supervisor'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertRaisesRegexp(ValidationError, 'Please put the date the supervisor approved this Trip')

    def test_form_validation_for_approved_by_budget_owner(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['approved_by_budget_owner'] = True
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertRaisesRegexp(ValidationError, 'Please put the date the budget owner approved this Trip')

    def test_form_validation_for_status_approved(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['status'] = u'approved'
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertRaisesRegexp(ValidationError,  'Only the supervisor can approve this trip')

    def test_form_validation_for_completed_no_report(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'advocacy'
        trip_dict['status'] = u'completed'
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertRaisesRegexp(ValidationError, 'You must provide a narrative report before the trip can be completed')

    def test_form_validation_for_staff_development(self):
        trip_dict = to_dict(self.trip)
        trip_dict['travel_type'] = u'staff_development'
        trip_dict['status'] = u'completed'
        form = TripForm(data=trip_dict)
        self.assertFalse(form.is_valid())
        self.assertRaisesRegexp(ValidationError,
                                'STAFF DEVELOPMENT trip must be certified by Human Resources'
                                'before it can be completed')

    def test_form_validation_for_date_greater(self):
        form = TravelRoutesForm(data={'origin': 'Test',
                                      'destination': 'Test',
                                      'depart': datetime.now() + timedelta(hours=3),
                                      'arrive': datetime.now()})
        self.assertFalse(form.is_valid())
        self.assertRaisesRegexp(ValidationError, 'test')

    def test_form_validation_for_dates(self):
        form = TravelRoutesForm(data={'origin': 'Test',
                                      'destination': 'Test',
                                      'depart': datetime.now() + timedelta(hours=3),
                                      'arrive': datetime.now() + timedelta(days=3)})
        self.assertFalse(form.is_valid())
        self.assertRaisesRegexp(ValidationError, 'Arrival must be greater than departure')