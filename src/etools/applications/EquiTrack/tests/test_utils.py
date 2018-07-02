from datetime import datetime

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase

import mock
from freezegun import freeze_time

from etools.applications.EquiTrack import utils
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory

PATH_SET_TENANT = "etools.applications.EquiTrack.utils.connection.set_tenant"


class TestUtils(SimpleTestCase):
    """
    Test utils function
    """

    @freeze_time("2013-05-26")
    def test_get_current_year(self):
        """test get current year function"""

        current_year = utils.get_current_year()
        self.assertEqual(current_year, 2013)

    @freeze_time("2013-05-26")
    def test_get_quarter_default(self):
        """test current quarter function"""
        quarter = utils.get_quarter()
        self.assertEqual(quarter, 'q2')

    def test_get_quarter(self):
        """test current quarter function"""
        quarter = utils.get_quarter(datetime(2016, 10, 1))
        self.assertEqual(quarter, 'q4')


class TestSetCountry(BaseTenantTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.mock_set = mock.Mock()
        self.country = self.user.profile.country

    def test_set_country(self):
        request = self.factory.get("/")
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)

    def test_set_country_override(self):
        """Ideally we would be setup a different country
        But having issues creating another country outside of current schema
        """
        self.user.profile.countries_available.add(self.country)
        request = self.factory.get("/?{}={}".format(
            settings.SCHEMA_OVERRIDE_PARAM,
            self.country.name
        ))
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)

    def test_set_country_override_shortcode(self):
        """Ideally we would be setup a different country
        But having issues creating another country outside of current schema
        """
        self.user.profile.countries_available.add(self.country)
        request = self.factory.get(
            "/?{}={}".format(
                settings.SCHEMA_OVERRIDE_PARAM,
                self.country.country_short_code
            )
        )
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)

    def test_set_country_override_invalid(self):
        request = self.factory.get("/?{}=Wrong".format(
            settings.SCHEMA_OVERRIDE_PARAM
        ))
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)

    def test_set_country_override_not_avialable(self):
        """Ideally we would be setup a different country
        But having issues creating another country outside of current schema
        """
        self.user.profile.countries_available.remove(self.country)
        request = self.factory.get("/?{}={}".format(
            settings.SCHEMA_OVERRIDE_PARAM,
            self.country.name
        ))
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)
