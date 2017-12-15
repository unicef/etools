from __future__ import unicode_literals

from django.conf import settings

from mock import patch
from post_office.models import Email, EmailTemplate

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import FastTenantTestCase
from notification.models import Notification
from notification.tests.factories import NotificationFactory


class TestEmailNotification(FastTenantTestCase):

    def setUp(self):
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


class TestSendNotification(FastTenantTestCase):
    """
    Test General Notification sending. We currently only have email set up, so
    this only tests that if a non-email type is created, we don't do anything
    with it.
    """
    def test_send_not_email(self):
        """
        This just tests that if we currently send a non Email notification,
        sent_recipients doesn't get updated.
        """
        notification = NotificationFactory(type='SMS')
        notification.send_notification()
        self.assertEqual(notification.sent_recipients, [])


@patch('notification.models.mail')
class TestSendEmail(FastTenantTestCase):

    def test_success(self, mock_mail):
        "On successful notification, sent_recipients should be populated."
        notification = NotificationFactory(template_data={'foo': 'bar'})
        notification.send_mail()
        # we called send with all the proper args
        mock_mail.send.assert_called_with(
            recipients=notification.recipients,
            sender=settings.DEFAULT_FROM_EMAIL,
            template=notification.template_name,
            context=notification.template_data,
        )
        # we marked the recipients as sent
        self.assertEqual(notification.recipients, notification.sent_recipients)

    def test_sender_is_user(self, mock_mail):
        "If sender is a User, send from their email address"
        sender = UserFactory()
        notification = NotificationFactory(sender=sender)
        notification.send_mail()
        # we called send ...
        mock_mail.send.assert_called()
        call_kwargs = mock_mail.send.call_args[1]
        # ... with the proper email
        self.assertEqual(sender.email, call_kwargs['sender'])

    def test_sender_is_not_a_user(self, mock_mail):
        "If sender is not a User, send DEFAULT_FROM_EMAIL"
        notification = NotificationFactory()
        notification.send_mail()
        # we called send ...
        mock_mail.send.assert_called()
        call_kwargs = mock_mail.send.call_args[1]
        # ... with the proper email
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, call_kwargs['sender'])

    def test_template_data_is_dict(self, mock_mail):
        "We accept a dictionary for the template context."
        template_data = {'foo': 'bar'}
        notification = NotificationFactory(template_data=template_data)
        notification.send_mail()
        # we called send ...
        mock_mail.send.assert_called()
        call_kwargs = mock_mail.send.call_args[1]
        # ... with the proper context
        self.assertEqual({'foo': 'bar'}, call_kwargs['context'])

    def test_template_data_is_str(self, mock_mail):
        "We accept string data for the template context."
        template_data = '{"foo": "bar"}'
        notification = NotificationFactory(template_data=template_data)
        notification.send_mail()
        # we called send ...
        mock_mail.send.assert_called()
        call_kwargs = mock_mail.send.call_args[1]
        # ... with the proper context
        self.assertEqual({'foo': 'bar'}, call_kwargs['context'])

    def test_ignore_mail_sending_error(self, mock_mail):
        "If sending throws an error, we log and continue."
        mock_mail.send.side_effect = Exception()
        notification = NotificationFactory()
        with patch('notification.models.logger') as mock_logger:
            notification.send_mail()
        mock_logger.exception.assert_called_with('Failed to send mail.')
        # recipients weren't marked as successful
        self.assertEqual(notification.sent_recipients, [])
