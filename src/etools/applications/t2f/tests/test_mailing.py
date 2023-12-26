from unittest.mock import Mock, patch

from django.core import mail

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.publics.tests.factories import PublicsBusinessAreaFactory
from etools.applications.t2f.serializers.mailing import TravelMailSerializer
from etools.applications.t2f.tests.factories import ItineraryItemFactory, TravelFactory
from etools.applications.users.tests.factories import UserFactory


class MailingTest(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.traveler = UserFactory(first_name='Jane',
                                   last_name='Doe')
        cls.traveler.profile.vendor_number = 'usrvnd'
        cls.traveler.profile.save()

        cls.unicef_staff = UserFactory(is_staff=True,
                                       first_name='John',
                                       last_name='Doe')
        cls.travel = TravelFactory(traveler=cls.traveler,
                                   supervisor=cls.unicef_staff)
        ItineraryItemFactory(travel=cls.travel)
        ItineraryItemFactory(travel=cls.travel)
        mail.outbox = []

    def test_mailing(self):
        tenant_country = self.travel.traveler.profile.country
        tenant_country.business_area_code = '0'
        tenant_country.save()
        PublicsBusinessAreaFactory(code=self.travel.traveler.profile.country.business_area_code)

        mock_send = Mock()
        with patch("etools.applications.t2f.models.send_notification", mock_send):
            self.travel.submit_for_approval()
            self.travel.approve()
            self.travel.report_note = 'Note'
            self.travel.mark_as_completed()

        self.assertEqual(mock_send.call_count, 3)

        for email in mail.outbox:
            self.assertIn(self.travel.reference_number, email.subject, email.subject)

    def test_mailing_serializer(self):
        serializer = TravelMailSerializer(self.travel, context={})
        self.assertKeysIn(['reference_number',
                           'supervisor',
                           'end_date',
                           'rejection_note',
                           'currency',
                           'estimated_travel_cost',
                           'location',
                           'traveler',
                           'start_date',
                           'purpose'],
                          serializer.data,
                          exact=True)
