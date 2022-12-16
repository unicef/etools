
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory
from etools.libraries.monitoring.service_checks import check_celery, check_db


class TestCheckDB(BaseTenantTestCase):
    def test_no_users(self):
        # if --keepdb flag used Users probably exist in db
        # so ignore this test if that is the case
        if not get_user_model().objects.exists():
            check = check_db()
            self.assertFalse(check.success)
            self.assertEqual(
                check.message,
                "{}:OK No users found in postgres".format(
                    settings.DATABASES["default"]["NAME"]
                )
            )

    def test_users(self):
        if not get_user_model().objects.exists():
            UserFactory()
        check = check_db()
        self.assertTrue(check.success)
        self.assertEqual(
            check.message,
            "{}:OK Successfully got a user from postgres".format(
                settings.DATABASES["default"]["NAME"]
            )
        )


class TestCheckCelery(SimpleTestCase):
    def test_valid(self):

        mock_celery = Mock()
        mock_celery.connection.return_value = Mock(connected=True)

        with patch("etools.libraries.monitoring.service_checks.Celery", Mock(return_value=mock_celery)):
            check = check_celery()
        self.assertTrue(check.success)
        self.assertEqual(
            check.message,
            "Celery connected"
        )

    def test_invalid(self):

        mock_celery = Mock()
        mock_celery.connection.return_value = Mock(connected=False)

        with patch("etools.libraries.monitoring.service_checks.Celery", Mock(return_value=mock_celery)):
            check = check_celery()
        self.assertFalse(check.success)
        self.assertEqual(
            check.message,
            "Celery unable to connect"
        )
