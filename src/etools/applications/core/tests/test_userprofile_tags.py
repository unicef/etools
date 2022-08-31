from unittest.mock import Mock

from etools.applications.core.templatetags.etools import show_country_select
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.users.tests.factories import GroupFactory, ProfileFactory, RealmFactory


class TestShowCountrySelect(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = ProfileFactory()
        cls.country = cls.profile.country
        cls.realm = RealmFactory(
            user=cls.profile.user,
            country=cls.country,
            organization=OrganizationFactory(),
            group=GroupFactory()
        )

    def test_no_profile(self):
        self.assertEqual(show_country_select({}, None), "")

    def test_country_single(self):
        res = show_country_select({}, self.profile)
        self.assertEqual(
            res,
            '<select id="country_selection">'
            '<option value="{}" selected>{}</option></select>'.format(
                self.country.pk,
                self.country.name
            )
        )

    def test_country_opts(self):
        mock_opts = Mock(app_label="reports")
        res = show_country_select({"opts": mock_opts}, self.profile)
        self.assertEqual(
            res,
            '<select id="country_selection">'
            '<option value="{}" selected>{}</option></select>'.format(
                self.country.pk,
                self.country.name
            )
        )
