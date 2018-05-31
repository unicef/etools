from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory

SEND_PATH = "etools.applications.tokens.views.send_notification_using_email_template"


class TestTokenEmailAuthView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")

    def setUp(self):
        self.client = Client()

    def test_get(self):
        response = self.client.get(reverse("tokens:login"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_post(self):
        email = "test-email-auth@example.com"
        UserFactory(email=email)
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
        UserFactory()
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

    def test_post_invalid_inactive_user(self):
        email = "test-email-auth@example.com"
        UserFactory(email=email, is_active=False)
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


class TestTokenGetView(BaseTenantTestCase):
    def setUp(self):
        self.client = Client()

    def test_get_not_logged_in(self):
        response = self.client.get(reverse("tokens:get"))
        self.assertEquals(response.status_code, status.HTTP_302_FOUND)

    def test_get_new(self):
        user = UserFactory()
        token_qs = Token.objects.filter(user=user)
        self.assertFalse(token_qs.exists())
        self.client.force_login(user)
        response = self.client.get(reverse("tokens:get"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(token_qs.exists())
        token = token_qs.first()
        self.assertEqual(response.data, {"token": token.key})

    def test_get_exists(self):
        user = UserFactory()
        token, _ = Token.objects.get_or_create(user=user)
        self.client.force_login(user)
        response = self.client.get(reverse("tokens:get"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"token": token.key})


class TestTokenResetView(BaseTenantTestCase):
    def setUp(self):
        self.client = Client()

    def test_get_not_logged_in(self):
        response = self.client.get(reverse("tokens:reset"))
        self.assertEquals(response.status_code, status.HTTP_302_FOUND)

    def test_get_none(self):
        user = UserFactory()
        token_qs = Token.objects.filter(user=user)
        self.assertFalse(token_qs.exists())
        self.client.force_login(user)
        response = self.client.get(reverse("tokens:reset"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(token_qs.exists())
        token = token_qs.first()
        self.assertEqual(response.data, {"token": token.key})

    def test_get_exists(self):
        user = UserFactory()
        token, _ = Token.objects.get_or_create(user=user)
        self.client.force_login(user)
        response = self.client.get(reverse("tokens:reset"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data["token"], token.key)


class TestTokenDeleteView(BaseTenantTestCase):
    def setUp(self):
        self.client = Client()

    def test_get_not_logged_in(self):
        response = self.client.get(reverse("tokens:delete"))
        self.assertEquals(response.status_code, status.HTTP_302_FOUND)

    def test_get_none(self):
        user = UserFactory()
        token_qs = Token.objects.filter(user=user)
        self.assertFalse(token_qs.exists())
        self.client.force_login(user)
        response = self.client.get(reverse("tokens:delete"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"message": "Token has been deleted."})
        self.assertFalse(token_qs.exists())

    def test_get_exists(self):
        user = UserFactory()
        token, _ = Token.objects.get_or_create(user=user)
        self.client.force_login(user)
        response = self.client.get(reverse("tokens:delete"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"message": "Token has been deleted."})
        self.assertFalse(Token.objects.filter(user=user).exists())
