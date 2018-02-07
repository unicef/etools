from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from mock import patch, Mock

from django.core.urlresolvers import reverse
from django.test import Client
from rest_framework import status

from EquiTrack.tests.mixins import FastTenantTestCase
from users.tests.factories import UserFactory


class TestCheckView(FastTenantTestCase):
    def setUp(self):
        super(TestCheckView, self).setUp()
        self.client = Client()
        self.url = reverse("monitoring")

    def test_get_success(self):
        UserFactory()
        mock_ping = Mock()
        mock_ping.control.ping.return_value = [1, 2]
        mock_celery = Mock(return_value=mock_ping)
        with patch("monitoring.service_checks.Celery", mock_celery):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, "all is well (checked: celery, db)")

    def test_get_fail(self):
        mock_ping = Mock()
        mock_ping.control.ping.return_value = []
        mock_celery = Mock(return_value=mock_ping)
        with patch("monitoring.service_checks.Celery", mock_celery):
            response = self.client.get(self.url)
        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.assertIn(
            "No running Celery workers were found.",
            response.content
        )
