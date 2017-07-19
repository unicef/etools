import datetime

from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from EquiTrack.factories import NotificationFactory

from post_office.models import EmailTemplate, Email

from notification.models import Notification


class TestEmailNotification(TenantTestCase):

    def setUp(self):
        self.date = datetime.date.today()
        self.tenant.country_short_code = 'LEBA'
        self.tenant.save()

        if EmailTemplate.objects.count() == 0:
            self.fail("No EmailTemplate instances found. Is the migration run?")

    def test_email_template_html_content_lookup(self):
        non_existing_template_content = Notification.get_template_html_content('random/template/name')

        self.assertEqual(non_existing_template_content, '')

        valid_template_content = Notification.get_template_html_content('trips/trip/created/updated')

        self.assertNotEqual(valid_template_content, '')

    def test_email_template_context_entry_lookup(self):
        non_existing_template_context_entries = Notification.get_template_context_entries('random/template/name')

        self.assertEqual(non_existing_template_context_entries, [])

        valid_template_context_entries = Notification.get_template_context_entries('trips/trip/created/updated')

        self.assertNotEqual(valid_template_context_entries, [])

    def test_send_notification(self):
        old_email_count = Email.objects.count()
        valid_notification = NotificationFactory()
        valid_notification.send_notification()

        self.assertListEqual(valid_notification.recipients, valid_notification.sent_recipients)
        self.assertEqual(Email.objects.count(), old_email_count + 1)
