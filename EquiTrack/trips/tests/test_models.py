__author__ = 'jcranwellward'

from datetime import datetime

from django.core import mail
from django.test import TestCase

from EquiTrack.factories import TripFactory, UserFactory

from trips.models import Trip


class TestTripModels(TestCase):

    def setUp(self):
        self.trip = TripFactory(
            owner__first_name='Fred',
            owner__last_name='Test',
            purpose_of_travel='To test some trips'
        )

    def test_create_trip(self):
        """
        Test a basic trip and make sure no emails are sent when planning
        """
        self.assertEqual(Trip.PLANNED, self.trip.status)
        self.assertEqual('To test some trips', self.trip.purpose_of_travel)
        self.assertEqual(Trip.PROGRAMME_MONITORING, self.trip.travel_type)
        self.assertFalse(self.trip.security_clearance_required)
        self.assertFalse(self.trip.international_travel)
        self.assertIsNotNone(self.trip.from_date)
        self.assertIsNotNone(self.trip.to_date)
        self.assertFalse(self.trip.ta_required)
        self.assertEqual(len(mail.outbox), 0)  # no emails should be sent


    def test_submit_trip(self):
        """
        Test that when a trip is submitted, the supervisor is informed
        """
        self.trip.status = Trip.SUBMITTED
        self.trip.save()
        self.assertEqual(Trip.SUBMITTED, self.trip.status)
        self.assertEqual(len(mail.outbox), 1)

        # Now test the email is correct for this action
        self.assertTrue(self.trip.owner.first_name in mail.outbox[0].subject)
        self.assertTrue('Submitted' in mail.outbox[0].subject)
        self.assertTrue('Submitted' in mail.outbox[0].body)
        self.assertTrue(self.trip.supervisor.email in mail.outbox[0].to)
        self.assertTrue(self.trip.owner.email in mail.outbox[0].to)

    def test_approve_trip(self):
        """
        Test that if a supervisor approves a trip, the trip status should
        automatically be marked as approved and date automatically assigned
        """
        self.trip.status = Trip.SUBMITTED  # force trip to submitted state
        self.trip.approved_by_supervisor = True
        self.trip.date_supervisor_approved = datetime.now()
        self.trip.save()
        self.assertEqual(Trip.APPROVED, self.trip.status)
        self.assertIsNotNone(self.trip.approved_date)

        # Now test the email is correct for this action
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(self.trip.approved_email_sent)
        self.assertTrue('Approved' in mail.outbox[0].subject)
        self.assertTrue('approved' in mail.outbox[0].body)
        self.assertTrue(self.trip.supervisor.email in mail.outbox[0].to)
        self.assertTrue(self.trip.owner.email in mail.outbox[0].to)

    def test_approve_trip_with_TA(self):
        """
        Test a more complex trip
        """
        self.trip.status = Trip.APPROVED
        self.trip.ta_required = True
        self.trip.approved_by_supervisor = True
        self.trip.date_supervisor_approved = datetime.now()
        self.trip.programme_assistant = UserFactory()
        self.trip.approved_email_sent = True
        self.trip.save()
        self.assertEqual(Trip.APPROVED, self.trip.status)
        self.assertEqual(len(mail.outbox), 1)

        # Now test the email is correct for this action
        self.assertTrue(self.trip.programme_assistant.first_name in mail.outbox[0].subject)


    def test_complete_trip(self):
        self.trip.status = Trip.COMPLETED
        self.trip.save()
        self.assertEqual(Trip.COMPLETED, self.trip.status)

        # Now test the email is correct for this action
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue('Completed' in mail.outbox[0].subject)
        self.assertTrue('completed' in mail.outbox[0].body)
        self.assertTrue(self.trip.supervisor.email in mail.outbox[0].to)
        self.assertTrue(self.trip.owner.email in mail.outbox[0].to)

    def test_cancel_trip(self):
        self.trip.status = Trip.CANCELLED
        self.trip.save()
        self.assertEqual(Trip.CANCELLED, self.trip.status)

        # Now test the email is correct for this action
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue('Cancelled' in mail.outbox[0].subject)
        self.assertTrue('cancelled' in mail.outbox[0].body)
        self.assertTrue(self.trip.supervisor.email in mail.outbox[0].to)
        self.assertTrue(self.trip.owner.email in mail.outbox[0].to)

