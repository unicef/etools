
from django.urls import reverse
from django.test import Client

from mock import Mock, patch
from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class TestCheckView(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.url = reverse("monitoring:monitoring")

    def test_get_success(self):
        UserFactory()
        mock_ping = Mock()
        mock_ping.control.ping.return_value = [1, 2]
        mock_celery = Mock(return_value=mock_ping)
        with patch("etools.libraries.monitoring.service_checks.Celery", mock_celery):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode('utf-8'), "all is well (checked: celery, db)")

    def test_get_fail(self):
        mock_ping = Mock()
        mock_ping.control.ping.return_value = []
        mock_celery = Mock(return_value=mock_ping)
        with patch("etools.libraries.monitoring.service_checks.Celery", mock_celery):
            response = self.client.get(self.url)
        self.assertContains(
            response,
            "No running Celery workers were found.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
