
import json
from unittest import skip

from django.conf import settings
from django.contrib.auth import get_user_model

from mock import Mock, patch
from tenant_schemas.utils import schema_context

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase, SCHEMA_NAME
from etools.applications.users import tasks
from etools.applications.users.models import UserProfile
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, ProfileFactory, UserFactory
from etools.applications.vision.vision_data_synchronizer import VISION_NO_DATA_MESSAGE, VisionException


class TestUserMapper(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group = GroupFactory(name="UNICEF User")

    def setUp(self):
        self.mapper = tasks.UserMapper()

    def test_init(self):
        self.assertEqual(self.mapper.countries, {})
        self.assertEqual(self.mapper.groups, {self.group.name: self.group})

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
        self.assertCountEqual(self.mapper.countries, {
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
        self.assertCountEqual(self.mapper.countries, {
            "UAT": country_uat,
            area_code: country,
        })

    def test_set_special_attr_country_override(self):
        """If country attribute, but override is set then False"""
        country = CountryFactory()
        profile = UserProfile(country_override=country)
        res = self.mapper._set_special_attr(profile, "country", "Change")
        self.assertFalse(res)

    def test_set_special_attr_country_match(self):
        """If country attribute matches, then False"""
        name = "test"
        country = CountryFactory(name=name)
        profile = UserProfile(country=country)
        self.mapper.countries = {name: country, "UAT": country}
        res = self.mapper._set_special_attr(profile, "country", country)
        self.assertEqual(profile.country, country)
        self.assertFalse(res)

    def test_set_special_attr(self):
        """If country attribute, no override and country does not
        match current county, then set and return True
        """
        name = "test"
        country = CountryFactory(name=name)
        self.mapper.countries = {name: country, "UAT": country}
        profile = ProfileFactory(country=None)
        self.assertIsNone(profile.country)
        self.assertFalse(profile.countries_available.count())
        res = self.mapper._set_special_attr(profile, "country", name)
        self.assertTrue(res)
        self.assertEqual(profile.country, country)
        self.assertTrue(profile.countries_available.count())

    def test_set_attribute_special_field(self):
        """If special field, use _set_special_attr method"""
        name = "test"
        country = CountryFactory(name=name)
        self.mapper.countries = {name: country, "UAT": country}
        profile = ProfileFactory(country=None)
        self.assertIsNone(profile.country)
        self.assertFalse(profile.countries_available.count())
        res = self.mapper._set_attribute(profile, "country", name)
        self.assertTrue(res)
        self.assertEqual(profile.country, country)
        self.assertTrue(profile.countries_available.count())

    def test_create_or_update_user_missing_fields(self):
        """If missing field, then don't create user record'"""
        email = "tester@example.com"
        res = self.mapper.create_or_update_user({"internetaddress": email})
        self.assertIsNone(res)
        self.assertFalse(get_user_model().objects.filter(email=email).exists())

    def test_create_or_update_user_created(self):
        """Ensure user is created and added to default group"""
        email = "tester@example.com"
        res = self.mapper.create_or_update_user({
            "internetaddress": email,
            "givenName": "Tester",
            "mail": email,
            "sn": "Last"
        })
        self.assertIsNone(res)
        self.assertTrue(get_user_model().objects.filter(email=email).exists())
        self.assertTrue(
            UserProfile.objects.filter(user__email=email).exists()
        )
        user = get_user_model().objects.get(email=email)
        self.assertIn(self.group, user.groups.all())

    def test_create_or_update_user_exists(self):
        """Ensure graceful handling if user already exists"""
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
        user = get_user_model().objects.get(email=email)
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
        self.assertTrue(get_user_model().objects.filter(email=email).exists())
        self.assertTrue(
            UserProfile.objects.filter(user__email=email).exists()
        )
        profile = UserProfile.objects.get(user__email=email)
        self.assertEqual(profile.phone_number, phone)


@skip("Issues with using public schema")
class TestSyncUsers(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mock_log = Mock()

    def test_sync(self):
        mock_sync = Mock()
        with patch("etools.applications.users.tasks.VisionSyncLog", self.mock_log):
            with patch("etools.applications.users.tasks.sync_users_remote", mock_sync):
                tasks.sync_users()
        self.assertEqual(mock_sync.call_count, 1)
        self.assertTrue(self.mock_log.call_count(), 1)
        self.assertTrue(self.mock_log.save.call_count(), 1)

    def test_sync_exception(self):
        mock_sync = Mock(side_effect=Exception)
        with patch("etools.applications.users.tasks.VisionSyncLog", self.mock_log):
            with patch("etools.applications.users.tasks.sync_users_remote", mock_sync):
                with self.assertRaises(VisionException):
                    tasks.sync_users()
        self.assertTrue(self.mock_log.call_count(), 1)
        self.assertTrue(self.mock_log.save.call_count(), 1)


@skip("Issues with using public schema")
class TestMapUsers(BaseTenantTestCase):
    @classmethod
    def setUpTestMethod(cls):
        cls.mock_log = Mock()

    def test_map(self):
        profile = ProfileFactory()
        profile.staff_id = profile.user.pk
        profile.save()
        data = {
            "ORG_UNIT_NAME": "UNICEF",
            "STAFF_ID": profile.staff_id,
            "MANAGER_ID": "",
            "ORG_UNIT_CODE": "101",
            "VENDOR_CODE": "202",
            "STAFF_EMAIL": "map@example.com",
            "STAFF_POST_NO": "123",
        }
        mock_request = Mock()
        mock_request.get().json.return_value = json.dumps([data])
        mock_request.get().status_code = 200
        with patch("etools.applications.users.tasks.VisionSyncLog", self.mock_log):
            with patch("etools.applications.users.tasks.requests", mock_request):
                tasks.map_users()
        self.assertTrue(self.mock_log.call_count(), 1)
        self.assertTrue(self.mock_log.save.call_count(), 1)

    def test_map_exception(self):
        mock_mapper = Mock(side_effect=Exception)
        with patch("etools.applications.users.tasks.VisionSyncLog", self.mock_log):
            with patch("etools.applications.users.tasks.UserMapper", mock_mapper):
                with self.assertRaises(VisionException):
                    tasks.map_users()
        self.assertTrue(self.mock_log.call_count(), 1)
        self.assertTrue(self.mock_log.save.call_count(), 1)


class TestUserVisionSynchronizer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.synchronizer = tasks.UserVisionSynchronizer(
            "GetOrgChartUnitsInfo_JSON",
            "end"
        )

    def setUp(self):
        super(TestUserVisionSynchronizer, self).setUp()
        self.record = {
            "ORG_UNIT_NAME": "UNICEF",
            "STAFF_ID": "123",
            "MANAGER_ID": "321",
            "ORG_UNIT_CODE": "101",
            "VENDOR_CODE": "202",
            "STAFF_EMAIL": "staff@example.com",
        }

    def test_init(self):
        synchronizer = tasks.UserVisionSynchronizer(
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
            tasks.UserVisionSynchronizer.REQUIRED_KEYS_MAP[
                "GetOrgChartUnitsInfo_JSON"
            ]
        )

    def test_get_json_no_data(self):
        self.assertEqual(
            self.synchronizer._get_json(VISION_NO_DATA_MESSAGE),
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
        with patch("etools.applications.users.tasks.requests", mock_request):
            res = self.synchronizer._load_records()
        self.assertEqual(res, self.record)

    def test_load_records_exception(self):
        mock_request = Mock()
        mock_request.get().status_code = 403
        with patch("etools.applications.users.tasks.requests", mock_request):
            with self.assertRaises(VisionException):
                self.synchronizer._load_records()

    def test_convert_records(self):
        self.assertEqual(self.synchronizer._convert_records('{}'), {})

    def test_response(self):
        mock_request = Mock()
        mock_request.get().json.return_value = json.dumps([self.record])
        mock_request.get().status_code = 200
        with patch("etools.applications.users.tasks.requests", mock_request):
            self.assertEqual(self.synchronizer.response, [self.record])
