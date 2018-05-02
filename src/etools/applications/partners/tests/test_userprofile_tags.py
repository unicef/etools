
from mock import Mock

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.templatetags import userprofile_tags as tags
from etools.applications.users.tests.factories import CountryFactory, ProfileFactory


class TestShowCountrySelect(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = CountryFactory()
        cls.profile = ProfileFactory(country=cls.country)
        cls.profile.countries_available.add(cls.country)

    def test_no_profile(self):
        self.assertEqual(tags.show_country_select({}, None), "")

    def test_country_single(self):
        res = tags.show_country_select({}, self.profile)
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
        res = tags.show_country_select({"opts": mock_opts}, self.profile)
        self.assertEqual(
            res,
            '<select id="country_selection">'
            '<option value="{}" selected>{}</option></select>'.format(
                self.country.pk,
                self.country.name
            )
        )
