import datetime
from typing import NamedTuple
from unittest import skip
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django_tenants.utils import schema_context

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.models import Organization
from etools.applications.users import tasks
from etools.applications.users.models import UserProfile
from etools.applications.users.tasks import sync_realms_to_prp
from etools.applications.users.tests.factories import (
    CountryFactory,
    GroupFactory,
    ProfileFactory,
    RealmFactory,
    SCHEMA_NAME,
    UserFactory,
)


class TestUserMapper(BaseTenantTestCase):
    fixtures = ['organizations']

    @classmethod
    def setUpTestData(cls):
        cls.group = GroupFactory(name="UNICEF User")

    def setUp(self):
        self.mapper = tasks.AzureUserMapper()

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
        self.assertEqual(profile.countries_available.count(), 1)  # Unicef Realm exists for user
        res = self.mapper._set_special_attr(profile, "country", name)
        self.assertTrue(res)
        self.assertEqual(profile.country, country)
        self.assertEqual(profile.countries_available.count(), 1)

    def test_set_attribute_special_field(self):
        """If special field, use _set_special_attr method"""
        name = "test"
        country = CountryFactory(name=name)
        self.mapper.countries = {name: country, "UAT": country}
        profile = ProfileFactory(country=None)
        self.assertIsNone(profile.country)
        self.assertEqual(profile.countries_available.count(), 1)  # Unicef Realm exists for user
        res = self.mapper._set_attribute(profile, "country", name)
        self.assertTrue(res)
        self.assertEqual(profile.country, country)
        self.assertTrue(profile.countries_available.count())

    def test_create_or_update_user_missing_fields(self):
        """If missing field, then don't create user record'"""
        email = "tester@example.com"
        res = self.mapper.create_or_update_user({"userPrincipalName": email})
        self.assertEqual(res, {'processed': 1, 'created': 0, 'updated': 0, 'skipped': 1, 'errors': 0})
        self.assertFalse(get_user_model().objects.filter(email=email).exists())

    def test_create_or_update_user_created(self):
        """Ensure user is created and added to default group"""
        country_uat = CountryFactory(name="UAT", business_area_code="UAT")
        self.mapper.countries = {"UAT": country_uat}
        email = "tester@example.com"
        res = self.mapper.create_or_update_user({
            "userPrincipalName": email,
            "internetaddress": email,
            "givenName": "Tester",
            "mail": email,
            "surname": "Last",
            "userType": "Internal",
            "companyName": "UNICEF",
            "extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute1": "test"
        })
        self.assertEqual(res, {'processed': 1, 'created': 1, 'updated': 0, 'skipped': 0, 'errors': 0})
        self.assertTrue(get_user_model().objects.filter(email=email).exists())
        self.assertTrue(
            UserProfile.objects.filter(user__email=email).exists()
        )
        user = get_user_model().objects.get(email=email)
        self.assertEqual(user.realms.count(), 1)
        self.assertEqual(
            user.profile.organization,
            Organization.objects.get(name='UNICEF', vendor_number='000')
        )

    def test_create_or_update_user_exists(self):
        """Ensure graceful handling if user already exists"""
        country_uat = CountryFactory(name="UAT")
        self.mapper.countries = {"UAT": country_uat}
        email = "tester@example.com"
        user = UserFactory(
            email=email,
            username=email,
            first_name="Tester",
            last_name="Last",
        )
        user.email = email
        user.save()
        res = self.mapper.create_or_update_user({
            "userPrincipalName": email,
            "internetaddress": email,
            "givenName": "Tester",
            "mail": email,
            "surname": "Last",
            "userType": "Internal",
            "companyName": "UNICEF",

        })
        self.assertEqual(res, {'processed': 1, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0})
        user = get_user_model().objects.get(email=email)
        self.assertIn(self.group, user.groups)

    def test_create_or_update_user_profile_updated(self):
        """If profile field changed, then update profile record"""
        country_uat = CountryFactory(name="UAT")
        self.mapper.countries = {"UAT": country_uat}
        email = "tester@example.com"
        phone = "0987654321"
        res = self.mapper.create_or_update_user({
            "internetaddress": email,
            "userPrincipalName": email,
            "givenName": "Tester",
            "mail": email,
            "surname": "Last",
            "userType": "Internal",
            "companyName": "UNICEF",
            "businessPhones": phone
        })
        self.assertEqual(res, {'processed': 1, 'created': 1, 'updated': 0, 'skipped': 0, 'errors': 0})
        self.assertTrue(get_user_model().objects.filter(email=email).exists())
        self.assertTrue(
            UserProfile.objects.filter(user__email=email).exists()
        )
        profile = UserProfile.objects.get(user__email=email)
        self.assertEqual(profile.phone_number, phone)


class TestRealmsPRPExport(BaseTenantTestCase):
    @override_settings(PRP_API_ENDPOINT='http://example.com/api/')
    @patch('etools.applications.users.signals.sync_realms_to_prp.apply_async')
    @patch('etools.applications.partners.prp_api.requests.post')
    def test_realms_sync(self, requests_post_mock, sync_mock):
        class Response(NamedTuple):
            status_code: int
            text: str

        requests_post_mock.return_value = Response(200, '{}')
        sync_mock.side_effect = lambda *args, **_kwargs: sync_realms_to_prp(*args[0])

        user = UserFactory()
        with self.captureOnCommitCallbacks(execute=True) as commit_callbacks:
            realm = RealmFactory(user=user)
        sync_mock.assert_called_with((user.pk, realm.modified), eta=realm.modified + datetime.timedelta(minutes=5))
        requests_post_mock.assert_called()
        self.assertEqual(len(commit_callbacks), 1)
