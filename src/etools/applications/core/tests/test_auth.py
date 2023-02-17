from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase

from etools.applications.core import auth
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.models import Organization
from etools.applications.users.tests.factories import UserFactory

SOCIAL_AUTH_PATH = "etools.applications.core.auth.social_auth"
SOCIAL_USER_PATH = "etools.applications.core.auth.social_core_user"


class TestSocialDetails(SimpleTestCase):
    def setUp(self):
        self.details = {
            'username': 'social_username',
            'email': None,
            'fullname': 'Social Full User',
            'first_name': 'Social',
            'last_name': 'User'
        }
        self.mock_social = Mock()

    def test_details_missing_email(self):
        self.mock_social.social_details.return_value = {
            'details': self.details
        }
        with patch(SOCIAL_AUTH_PATH, self.mock_social):
            r = auth.social_details(
                None,
                {},
                {"idp": "123", "email": "test@example.com"}
            )
        self.details["idp"] = "123"
        self.details["email"] = "test@example.com"
        self.assertEqual(r, {"details": self.details})

    def test_details(self):
        self.details["email"] = "test@example.com"
        self.mock_social.social_details.return_value = {
            'details': self.details
        }
        with patch(SOCIAL_AUTH_PATH, self.mock_social):
            r = auth.social_details(
                None,
                {},
                {"idp": "123", "email": "new@example.com"}
            )
        self.details["idp"] = "123"
        self.assertEqual(r, {"details": self.details})


class TestGetUsername(BaseTenantTestCase):
    def setUp(self):
        self.details = {
            'username': 'social_username',
            'email': "test@example.com",
            'fullname': 'Social Full User',
            'first_name': 'Social',
            'last_name': 'User'
        }

    def test_user_exists(self):
        self.user = UserFactory(username=self.details["email"])
        r = auth.get_username(None, self.details, None)
        self.assertEqual(r, {"username": self.details["email"]})


class TestUserDetails(BaseTenantTestCase):
    fixtures = ('audit_groups', 'organizations')

    def setUp(self):
        self.details = {
            'username': 'social_username',
            'email': "test@example.com",
            'fullname': 'Social Full User',
            'first_name': 'Social',
            'last_name': 'User'
        }
        self.mock_social = Mock()
        self.mock_social.user_details.return_value = "Returned"

    def test_no_user(self):
        with patch(SOCIAL_USER_PATH, self.mock_social):
            r = auth.user_details("strategy", self.details, None, None)
        self.assertEqual(r, "Returned")
        self.mock_social.user_details.assert_called_with(
            "strategy",
            self.details,
            None,
            None
        )

    def test_no_update(self):
        user = UserFactory(
            username=self.details["email"],
            email=self.details["email"],
        )
        self.details["business_area_code"] = user.profile.country.business_area_code
        with patch(SOCIAL_USER_PATH, self.mock_social):
            r = auth.user_details("strategy", self.details, None, user)
        self.assertEqual(r, "Returned")
        self.mock_social.user_details.assert_called_with(
            "strategy",
            self.details,
            None,
            user
        )

    def test_no_profile_country(self):
        user = UserFactory(
            username=self.details["email"],
            email=self.details["email"],
        )
        country = user.profile.country
        self.details["business_area_code"] = country.business_area_code
        user.profile.country = None
        user.profile.save()
        self.assertIsNone(user.profile.country)
        with patch(SOCIAL_USER_PATH, self.mock_social):
            r = auth.user_details("strategy", self.details, None, user)
        self.assertEqual(r, "Returned")
        self.mock_social.user_details.assert_called_with(
            "strategy",
            self.details,
            None,
            user
        )
        user_updated = get_user_model().objects.get(pk=user.pk)
        self.assertEqual(user_updated.profile.country, country)

    def test_is_staff_update(self):
        user = UserFactory(
            realms__data=[],
            username=self.details["email"],
            email=self.details["email"],
        )

        country = user.profile.country
        user.profile.organization = None
        user.profile.save(update_fields=['organization'])
        self.assertIsNone(user.profile.organization)

        self.details["business_area_code"] = country.business_area_code
        self.details["idp"] = "UNICEF Azure AD"
        self.assertFalse(user.is_staff)
        with patch(SOCIAL_USER_PATH, self.mock_social):
            r = auth.user_details("strategy", self.details, None, user)
        self.assertEqual(r, "Returned")
        self.mock_social.user_details.assert_called_with(
            "strategy",
            self.details,
            None,
            user
        )
        user_updated = get_user_model().objects.get(pk=user.pk)
        self.assertTrue(user_updated.is_staff)
        self.assertEqual(
            user_updated.profile.organization,
            Organization.objects.get(name='UNICEF', vendor_number='000')
        )
