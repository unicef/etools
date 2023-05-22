from django.conf import settings
from django.test import RequestFactory

import mock

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory
from etools.libraries.tenant_support import utils

PATH_SET_TENANT = "etools.libraries.tenant_support.utils.connection.set_tenant"


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

    def test_set_country_override_not_available(self):
        """Ideally we would be setup a different country
        But having issues creating another country outside of current schema
        """
        self.user.realms.filter(country=self.country).delete()
        request = self.factory.get("/?{}={}".format(
            settings.SCHEMA_OVERRIDE_PARAM,
            self.country.name
        ))
        with mock.patch(PATH_SET_TENANT, self.mock_set):
            utils.set_country(self.user, request)
        self.assertEqual(request.tenant, self.country)
        self.mock_set.assert_called_with(self.country)
