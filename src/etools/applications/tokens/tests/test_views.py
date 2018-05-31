from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import Client
from django.urls import resolve, reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory

SEND_PATH = "etools.applications.tokens.views.send_notification_using_email_template"


class TestTokenAuthView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")

    def setUp(self):
        self.client =  Client()

    def test_get(self):
        response = self.client.get(reverse("tokens:login"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_post(self):
        email = "test-email-auth@example.com"
        user = UserFactory(email=email)
        mock_send = Mock()
        with patch(SEND_PATH, mock_send):
            response = self.client.post(
                reverse("tokens:login"),
                data={"email": email}
            )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_send.call_count, 1)

    def test_post_invalid_email(self):
        email = "test-email-auth@example.com"
        user = UserFactory()
        mock_send = Mock()
        with patch(SEND_PATH, mock_send):
            response = self.client.post(
                reverse("tokens:login"),
                data={"email": email}
            )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.context["form"].errors,
            {"__all__": ["User with such email does not exists."]}
        )
        self.assertEqual(mock_send.call_count, 0)

    def test_post_invalid_emailinactive_user(self):
        email = "test-email-auth@example.com"
        user = UserFactory(email=email, is_active=False)
        mock_send = Mock()
        with patch(SEND_PATH, mock_send):
            response = self.client.post(
                reverse("tokens:login"),
                data={"email": email}
            )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.context["form"].errors,
            {"__all__": ["This account is inactive."]}
        )
        self.assertEqual(mock_send.call_count, 0)
