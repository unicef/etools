import datetime
from unittest import skip

from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from EquiTrack.factories import NotificationFactory

from post_office.models import EmailTemplate

from notification.models import Notification


class TestEmailNotification(TenantTestCase):

    def setUp(self):
        self.date = datetime.date.today()
        self.tenant.country_short_code = 'LEBA'
        self.tenant.save()

    def test_email_template_html_content_lookup(self):
        if EmailTemplate.objects.count() == 0:
            self.fail("No EmailTemplate instances found. Is the migration run?")

        non_existing_template_content = Notification.get_template_html_content('random/template/name')

        self.assertEqual(non_existing_template_content, '')

        valid_template_content = Notification.get_template_html_content('trips/trip/created/updated')

        self.assertNotEqual(valid_template_content, '')
