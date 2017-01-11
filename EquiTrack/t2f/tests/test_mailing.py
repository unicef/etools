from __future__ import unicode_literals

from django.core import mail

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase

from .factories import TravelFactory


class MailingTest(APITenantTestCase):
    def setUp(self):
        super(MailingTest, self).setUp()
        self.traveler = UserFactory(first_name='Jane',
                                    last_name='Doe')
        self.unicef_staff = UserFactory(is_staff=True,
                                        first_name='John',
                                        last_name='Doe')
        self.travel = TravelFactory(traveler=self.traveler,
                                    supervisor=self.unicef_staff)

    def test_mailing(self):
        self.travel.submit_for_approval()
        self.travel.approve()
        self.travel.send_for_payment()
        self.travel.submit_certificate()
        self.travel.approve_certificate()
        self.travel.mark_as_certified()
        self.travel.mark_as_completed()

        self.assertEqual(len(mail.outbox), 7)
