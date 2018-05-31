from django.conf import settings
from django.test import Client
from django.urls import reverse
from drfpasswordless.utils import create_callback_token_for_user
from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class TestTokenAuthenticationMiddleware(BaseTenantTestCase):
    def setUp(self):
        self.client =  Client()

    def test_no_token(self):
        response = self.client.get(reverse("email_auth:login"))
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_token(self):
        user = UserFactory()
        token = create_callback_token_for_user(user, "email")
        response = self.client.get("{}?{}={}".format(
            reverse("email_auth:login"),
            settings.EMAIL_AUTH_TOKEN_NAME,
            token,
        ))
        self.assertEquals(response.status_code, status.HTTP_302_FOUND)

    def test_token_invalid(self):
        response = self.client.get("{}?{}={}".format(
            reverse("email_auth:login"),
            settings.EMAIL_AUTH_TOKEN_NAME,
            "wrong",
        ))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.context["form"].errors,
            {"__all__": ["Couldn't log you in. Invalid token."]}
        )
