from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from tenant_schemas.utils import schema_context
from unittest import skip

from EquiTrack.factories import (
    CountryFactory,
    GroupFactory,
    SectionFactory,
    ProfileFactory,
)
from EquiTrack.tests.mixins import SCHEMA_NAME, FastTenantTestCase
from users import tasks
from users.models import Section, UserProfile


class TestUserMapper(FastTenantTestCase):
    def setUp(self):
        super(TestUserMapper, self).setUp()
        self.group = GroupFactory(name='UNICEF User')
        self.mapper = tasks.UserMapper()

    def test_init(self):
        self.assertEqual(self.mapper.countries, {})
        self.assertEqual(self.mapper.sections, {})
        self.assertEqual(self.mapper.groups, {"UNICEF User": self.group})
        self.assertEqual(self.mapper.section_users, {})

    @skip("UAT country not found?!?!")
    def test_get_country_uat(self):
        """Check that we get country UAT if no match for business area code"""
        with schema_context(SCHEMA_NAME):
            country_uat = CountryFactory(name="UAT")
            res = self.mapper._get_country("UAT")
        self.assertEqual(res, country_uat)
        self.assertEqual(self.mapper.countries, {"UAT": country_uat})

    def test_get_country_business_area_code(self):
        """Check that we get country that matches business area code"""
        area_code = "10101"
        with schema_context(SCHEMA_NAME):
            country_uat = CountryFactory(name="UAT")
            self.mapper.countries = {"UAT": country_uat}
            country = CountryFactory(business_area_code=area_code)
            res = self.mapper._get_country(area_code)
        self.assertEqual(res, country)
        self.assertItemsEqual(self.mapper.countries, {
            area_code: country,
            "UAT": country_uat
        })

    def test_get_country_exists(self):
        """Check that if country exists and is set, we handle that properly"""
        area_code = "20202"
        country_uat = CountryFactory(name="UAT")
        country = CountryFactory(business_area_code=area_code)
        self.mapper.countries = {
            "UAT": country_uat,
            area_code: country,
        }
        res = self.mapper._get_country(area_code)
        self.assertEqual(res, country)
        self.assertItemsEqual(self.mapper.countries, {
            "UAT": country_uat,
            area_code: country,
        })

    def test_get_section(self):
        """Check that section is retrieved and set"""
        name = "Section"
        code = "Code"
        with schema_context(SCHEMA_NAME):
            section = SectionFactory(name=name, code=code)
            self.assertTrue(
                Section.objects.filter(name=name, code=code).exists()
            )
            res = self.mapper._get_section(name, code)
        self.assertEqual(res, section)
        self.assertEqual(self.mapper.sections, {name: section})

    def test_get_section_exists(self):
        """Check if section exsits and set already, it is handled properly"""
        name = "Section"
        code = "Code"
        section = SectionFactory(name=name, code=code)
        self.mapper.sections = {name: section}
        res = self.mapper._get_section(name, code)
        self.assertEqual(res, section)
        self.assertEqual(self.mapper.sections, {name: section})

    def test_get_section_create(self):
        """Check that is section does not exist, that one is created"""
        name = "Section"
        code = "Code"
        self.assertEqual(self.mapper.sections, {})
        res = self.mapper._get_section(name, code)
        self.assertTrue(isinstance(res, Section))
        self.assertEqual(self.mapper.sections.keys(), [name])
        with schema_context(SCHEMA_NAME):
            self.assertTrue(
                Section.objects.filter(name=name, code=code).exists()
            )

    def test_set_simple_attr_no_change(self):
        """If no change in attr value then return False"""
        section = Section(name="Name")
        res = self.mapper._set_simple_attr(section, "name", "Name")
        self.assertFalse(res)
        self.assertEqual(section.name, "Name")

    def test_set_simple_attr_change(self):
        """If change in attr value then return True"""
        section = Section(name="Name")
        res = self.mapper._set_simple_attr(section, "name", "Change")
        self.assertTrue(res)
        self.assertEqual(section.name, "Change")

    def test_set_special_attr_not_country(self):
        """Return False if attr is not country"""
        section = Section(name="Name")
        res = self.mapper._set_special_attr(section, "name", "Change")
        self.assertFalse(res)
        self.assertEqual(section.name, "Name")

    def test_set_special_attr_country_override(self):
        """If country attribute, but override is set then False"""
        country = CountryFactory()
        profile = UserProfile(country_override=country)
        res = self.mapper._set_special_attr(profile, "country", "Change")
        self.assertFalse(res)

    def test_set_special_attr_country_match(self):
        """If country attribute matches, then False"""
        code = "test"
        country = CountryFactory(code=code)
        profile = UserProfile(country=country)
        self.mapper.countries = {code: country, "UAT": country}
        res = self.mapper._set_special_attr(profile, "country", country)
        self.assertEqual(profile.country, country)
        self.assertFalse(res)

    def test_set_special_attr(self):
        """If country attribute, no override and country does not
        match current county, then set and return True
        """
        code = "test"
        country = CountryFactory(code=code)
        self.mapper.countries = {code: country, "UAT": country}
        profile = ProfileFactory(country=None)
        self.assertIsNone(profile.country)
        self.assertFalse(profile.countries_available.count())
        res = self.mapper._set_special_attr(profile, "country", code)
        self.assertTrue(res)
        self.assertEqual(profile.country, country)
        self.assertTrue(profile.countries_available.count())

    def test_set_attribute_char(self):
        section = Section(name="Initial")
        res = self.mapper._set_attribute(section, "name", "Change")
        self.assertTrue(res)
        self.assertEqual(section.name, "Change")

    def test_set_attribute_char_truncate(self):
        """If char field and value provided longer than allowed,
        then truncated
        """
        section = Section(name="Initial")
        res = self.mapper._set_attribute(section, "name", "1" * 70)
        self.assertTrue(res)
        self.assertEqual(section.name, "1" * 64)

    def test_set_attribute_blank(self):
        """Blank values are set to None"""
        section = Section(name="Initial")
        res = self.mapper._set_attribute(section, "name", "")
        self.assertTrue(res)
        self.assertIsNone(section.name)

    def test_set_attribute_section_code(self):
        """If section_code attribute, then set to last 4 chars of value"""
        profile = ProfileFactory()
        self.assertIsNone(profile.section_code)
        res = self.mapper._set_attribute(profile, "section_code", "12345678")
        self.assertTrue(res)
        self.assertEqual(profile.section_code, "5678")

    def test_set_attribute_special_field(self):
        """If special field, use _set_special_attr method"""
        code = "test"
        country = CountryFactory(code=code)
        self.mapper.countries = {code: country, "UAT": country}
        profile = ProfileFactory(country=None)
        self.assertIsNone(profile.country)
        self.assertFalse(profile.countries_available.count())
        res = self.mapper._set_attribute(profile, "country", code)
        self.assertTrue(res)
        self.assertEqual(profile.country, country)
        self.assertTrue(profile.countries_available.count())
