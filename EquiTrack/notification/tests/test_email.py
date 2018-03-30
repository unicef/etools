from __future__ import unicode_literals

from django.conf import settings
from django.core.management import call_command
from django.utils import six

from mock import mock, patch
from post_office.models import Email, EmailTemplate

from EquiTrack.tests.cases import BaseTenantTestCase
from notification.models import Notification
from notification.tests.factories import NotificationFactory
from users.tests.factories import UserFactory


class TestEmailNotification(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant.country_short_code = 'LEBA'
        cls.tenant.save()

        call_command('update_notifications')
        if EmailTemplate.objects.count() == 0:
            cls.fail("No EmailTemplate instances found. Is the migration run?")

    def test_send_notification(self):
        old_email_count = Email.objects.count()
        valid_notification = NotificationFactory()
        valid_notification.send_notification()

        six.assertCountEqual(self, valid_notification.recipients, valid_notification.sent_recipients)
        self.assertEqual(Email.objects.count(), old_email_count + 1)


class TestSendNotification(BaseTenantTestCase):
    """
    Test General Notification sending. We currently only have email set up, so
    this only tests that if a non-email type is created, it's an error
    to try to send it.
    """
    def test_send_not_email(self):
        """
        This just tests that if we currently send a non Email notification,
        sent_recipients doesn't get updated.
        """
        notification = NotificationFactory(type='SMS')
        with self.assertRaises(ValueError):
            notification.send_notification()
        self.assertEqual(notification.sent_recipients, [])


@patch('notification.models.mail')
class TestSendEmail(BaseTenantTestCase):

    def test_success(self, mock_mail):
        "On successful notification, sent_recipients should be populated."
        cc = ['joe@example.com']
        notification = NotificationFactory(
            template_data={'foo': 'bar'},
            cc=cc
        )
        mock_mail.send.return_value = Email()
        with mock.patch.object(Notification, 'save'):  # Don't actually try to save it
            notification.send_mail()
        # we called send with all the proper args
        mock_mail.send.assert_called_with(
            recipients=notification.recipients,
            cc=cc,
            sender=settings.DEFAULT_FROM_EMAIL,
            template=notification.template_name,
            context=notification.template_data,
            html_message='',
            message='',
            subject='',
        )
        # we marked the recipients as sent
        self.assertEqual(notification.recipients + cc, notification.sent_recipients)

    def test_sender_is_user(self, mock_mail):
        "If sender is a User, send from their email address"
        sender = UserFactory()
        notification = NotificationFactory(sender=sender)
        mock_mail.send.return_value = Email()
        with mock.patch.object(Notification, 'save'):  # Don't actually try to save it
            notification.send_mail()
        # we called send ...
        mock_mail.send.assert_called()
        call_kwargs = mock_mail.send.call_args[1]
        # ... with the proper email
        self.assertEqual(sender.email, call_kwargs['sender'])

    def test_sender_is_not_a_user(self, mock_mail):
        "If sender is not a User, send DEFAULT_FROM_EMAIL"
        mock_mail.send.return_value = Email()
        notification = NotificationFactory()
        with mock.patch.object(Notification, 'save'):  # Don't actually try to save it
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
        mock_mail.send.return_value = Email()
        with mock.patch.object(Notification, 'save'):  # Don't actually try to save it
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
        mock_mail.send.return_value = Email()
        with mock.patch.object(Notification, 'save'):  # Don't actually try to save it
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
        mock_mail.send.return_value = Email()
        with mock.patch.object(Notification, 'save'):  # Don't actually try to save it
            with patch('notification.models.logger') as mock_logger:
                notification.send_mail()
        mock_logger.exception.assert_called_with('Failed to send mail.')
        # recipients weren't marked as successful
        self.assertEqual(notification.sent_recipients, [])
