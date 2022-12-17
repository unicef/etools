from unittest.mock import Mock, patch

from django.test import Client
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class TestCheckView(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.url = reverse("monitoring:app_ready")

    def test_get_success(self):
        UserFactory()
        mock_celery = Mock()
        mock_celery.connection.return_value = Mock(connected=True)
        with patch("etools.libraries.monitoring.service_checks.Celery", Mock(return_value=mock_celery)):
            response = self.client.get(self.url)
        self.assertEqual(response.content.decode('utf-8'), "all is well (checked: celery, db)")

    def test_get_fail(self):
        mock_celery = Mock()
        mock_celery.connection.return_value = Mock(connected=False)

        with patch("etools.libraries.monitoring.service_checks.Celery", Mock(return_value=mock_celery)):
            response = self.client.get(self.url)
        self.assertContains(
            response,
            "Celery unable to connect",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
