from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json

from django.conf import settings
from mock import patch, Mock
from tenant_schemas.utils import schema_context
from unittest import skip

from EquiTrack.factories import (
    CountryFactory,
    GroupFactory,
    SectionFactory,
    ProfileFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import SCHEMA_NAME, FastTenantTestCase
from users import tasks
from users.models import Section, User, UserProfile
from vision.vision_data_synchronizer import VisionException


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

    def test_create_or_update_user_missing_fields(self):
        """If missing field, then don't create user record'"""
        email = "tester@example.com"
        res = self.mapper.create_or_update_user({"internetaddress": email})
        self.assertIsNone(res)
        self.assertFalse(User.objects.filter(email=email).exists())

    def test_create_or_update_user_created(self):
        email = "tester@example.com"
        res = self.mapper.create_or_update_user({
            "internetaddress": email,
            "givenName": "Tester",
            "mail": email,
            "sn": "Last"
        })
        self.assertIsNone(res)
        self.assertTrue(User.objects.filter(email=email).exists())
        self.assertTrue(
            UserProfile.objects.filter(user__email=email).exists()
        )
        user = User.objects.get(email=email)
        self.assertIn(self.group, user.groups.all())

    def test_create_or_update_user_exists(self):
        email = "tester@example.com"
        user = UserFactory(
            email=email,
            username=email,
            first_name="Tester",
            last_name="Last",
        )
        res = self.mapper.create_or_update_user({
            "internetaddress": email,
            "givenName": "Tester",
            "mail": email,
            "sn": "Last"
        })
        self.assertIsNone(res)
        user = User.objects.get(email=email)
        self.assertIn(self.group, user.groups.all())

    def test_create_or_update_user_profile_updated(self):
        """If profile field changed, then update profile record"""
        email = "tester@example.com"
        phone = "0987654321"
        res = self.mapper.create_or_update_user({
            "internetaddress": email,
            "givenName": "Tester",
            "mail": email,
            "sn": "Last",
            "telephoneNumber": phone
        })
        self.assertIsNone(res)
        self.assertTrue(User.objects.filter(email=email).exists())
        self.assertTrue(
            UserProfile.objects.filter(user__email=email).exists()
        )
        profile = UserProfile.objects.get(user__email=email)
        self.assertEqual(profile.phone_number, phone)

    def test_set_supervisor_vacant(self):
        """If manager id is Vacant, return False"""
        profile = ProfileFactory()
        self.assertIsNone(profile.supervisor)
        self.assertFalse(self.mapper._set_supervisor(profile, "Vacant"))
        self.assertIsNone(profile.supervisor)

    def test_set_supervisor_none(self):
        """If manager id is None, return False"""
        profile = ProfileFactory()
        self.assertIsNone(profile.supervisor)
        self.assertFalse(self.mapper._set_supervisor(profile, None))
        self.assertIsNone(profile.supervisor)

    def test_set_supervisor_matches(self):
        """If manager matches, return False"""
        manager_id = "321"
        supervisor = ProfileFactory(staff_id=manager_id)
        profile = ProfileFactory()
        profile.supervisor = supervisor.user
        self.assertFalse(self.mapper._set_supervisor(profile, manager_id))

    def test_set_supervisor_does_not_exist(self):
        profile = ProfileFactory()
        self.assertIsNone(profile.supervisor)
        self.assertFalse(self.mapper._set_supervisor(profile, "404"))
        self.assertIsNone(profile.supervisor)

    def test_set_supervisor(self):
        manager_id = "321"
        supervisor = ProfileFactory(staff_id=manager_id)
        profile = ProfileFactory()
        self.mapper.section_user = {manager_id: supervisor}
        self.assertIsNone(profile.supervisor)
        self.assertTrue(self.mapper._set_supervisor(profile, manager_id))
        self.assertEqual(profile.supervisor, supervisor.user)


class TestUserSynchronizer(FastTenantTestCase):
    def setUp(self):
        super(TestUserSynchronizer, self).setUp()
        self.synchronizer = tasks.UserSynchronizer(
            "GetOrgChartUnitsInfo_JSON",
            "end"
        )
        self.record = {
            "ORG_UNIT_NAME": "UNICEF",
            "STAFF_ID": "123",
            "MANAGER_ID": "321",
            "ORG_UNIT_CODE": "101",
            "VENDOR_CODE": "202",
            "STAFF_EMAIL": "staff@example.com",
        }

    def test_init(self):
        synchronizer = tasks.UserSynchronizer(
            "GetOrgChartUnitsInfo_JSON",
            "end"
        )
        self.assertEqual(
            synchronizer.url,
            "{}/GetOrgChartUnitsInfo_JSON/end".format(
                settings.VISION_URL
            )
        )
        self.assertEqual(
            synchronizer.required_keys,
            tasks.UserSynchronizer.REQUIRED_KEYS_MAP[
                "GetOrgChartUnitsInfo_JSON"
            ]
        )

    def test_get_json_no_data(self):
        self.assertEqual(
            self.synchronizer._get_json("No Data Available"),
            "{}"
        )

    def test_get_json(self):
        data = {"test": "data"}
        self.assertEqual(self.synchronizer._get_json(data), data)

    def test_filter_records_no_key(self):
        """If key is not in the record provided then False"""
        self.assertFalse(self.synchronizer._filter_records([{}]))

    def test_filter_records_staff_email(self):
        """Ensure STAFF_EMAIL has a value"""
        self.record["STAFF_EMAIL"] = ""
        self.assertFalse(self.synchronizer._filter_records([self.record]))

    def test_filter_records(self):
        self.assertTrue(self.synchronizer._filter_records([self.record]))

    def test_load_records(self):
        mock_request = Mock()
        mock_request.get().json.return_value = self.record
        mock_request.get().status_code = 200
        with patch("users.tasks.requests", mock_request):
            res = self.synchronizer._load_records()
        self.assertEqual(res, self.record)

    def test_load_records_exception(self):
        mock_request = Mock()
        mock_request.get().status_code = 403
        with patch("users.tasks.requests", mock_request):
            with self.assertRaises(VisionException):
                self.synchronizer._load_records()

    def test_convert_records(self):
        self.assertEqual(self.synchronizer._convert_records('{}'), {})

    def test_response(self):
        mock_request = Mock()
        mock_request.get().json.return_value = json.dumps([self.record])
        mock_request.get().status_code = 200
        with patch("users.tasks.requests", mock_request):
            self.assertEqual(self.synchronizer.response, [self.record])
