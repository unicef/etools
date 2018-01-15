from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from mock import patch, Mock
from unittest import TestCase

from django.conf import settings

from EquiTrack.factories import UserFactory
from monitoring.service_checks import check_celery, check_db


class TestCheckDB(TestCase):
    def test_no_users(self):
        check = check_db()
        self.assertFalse(check.success)
        self.assertEqual(
            check.message,
            "{}:OK No users found in postgres".format(
                settings.DATABASES["default"]["NAME"]
            )
        )

    def test_users(self):
        UserFactory()
        check = check_db()
        self.assertTrue(check.success)
        self.assertEqual(
            check.message,
            "{}:OK Successfully got a user from postgres".format(
                settings.DATABASES["default"]["NAME"]
            )
        )


class TestCheckCelery(TestCase):
    def test_valid(self):
        mock_ping = Mock()
        mock_ping.control.ping.return_value = [1, 2]
        mock_celery = Mock(return_value=mock_ping)
        with patch("monitoring.service_checks.Celery", mock_celery):
            check = check_celery()
        self.assertTrue(check.success)
        self.assertEqual(
            check.message,
            "Successfully pinged 2 workers"
        )

    def test_invalid(self):
        mock_ping = Mock()
        mock_ping.control.ping.return_value = []
        mock_celery = Mock(return_value=mock_ping)
        with patch("monitoring.service_checks.Celery", mock_celery):
            check = check_celery()
        self.assertFalse(check.success)
        self.assertEqual(
            check.message,
            "No running Celery workers were found."
        )
