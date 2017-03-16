from __future__ import unicode_literals

from django.core import mail
from django.test.utils import override_settings

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f.models import Invoice
from publics.tests.factories import BusinessAreaFactory

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

    @override_settings(DISABLE_INVOICING=False)
    def test_mailing(self):
        tenant_country = self.travel.traveler.profile.country
        tenant_country.business_area_code = '0'
        tenant_country.save()
        BusinessAreaFactory(code=self.travel.traveler.profile.country.business_area_code)

        self.travel.submit_for_approval()
        self.travel.approve()
        self.travel.send_for_payment()
        self.travel.invoices.all().update(status=Invoice.SUCCESS)
        self.travel.submit_certificate()
        self.travel.approve_certificate()
        self.travel.mark_as_certified()
        self.travel.report_note = 'Note'
        self.travel.mark_as_completed()

        self.assertEqual(len(mail.outbox), 7)

        for email in mail.outbox:
            self.assertIn(self.travel.reference_number, email.subject, email.subject)
