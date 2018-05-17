
from unittest import skip

from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.urls import reverse

from mock import ANY, Mock, patch
from tenant_schemas.utils import schema_context

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.hact.tasks import update_hact_for_country
from etools.applications.users.admin import CountryAdmin, ProfileAdmin, ProfileInline, UserAdminPlus
from etools.applications.users.models import Country, User, UserProfile
from etools.applications.users.tests.factories import ProfileFactory, UserFactory


class MockRequest:
    pass


class TestProfileInline(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        site = AdminSite()
        cls.admin = ProfileInline(UserProfile, site)
        cls.request = MockRequest()
        cls.user = UserFactory()

    def test_get_fields(self):
        """If not superuser then remove country_override"""
        self.request.user = self.user
        self.assertFalse(self.request.user.is_superuser)
        fields = self.admin.get_fields(self.request)
        self.assertNotIn("country_override", fields)

    @skip("Appears that fields are maybe cached?")
    def test_get_fields_superuser(self):
        """If superuser then country_override stays"""
        self.request.user = self.superuser
        self.assertTrue(self.request.user.is_superuser)
        fields = self.admin.get_fields(self.request)
        self.assertIn("country_override", fields)


class TestProfileAdmin(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        site = AdminSite()
        cls.admin = ProfileAdmin(UserProfile, site)
        cls.request = MockRequest()
        cls.superuser = UserFactory(is_superuser=True)
        cls.user = UserFactory()

    def test_has_add_permission(self):
        self.assertFalse(self.admin.has_add_permission(self.request))

    def test_has_delete_permission(self):
        self.assertFalse(self.admin.has_delete_permission(self.request))

    def test_get_fields(self):
        """If not superuser then remove country_override"""
        self.request.user = self.user
        fields = self.admin.get_fields(self.request)
        self.assertNotIn("country_override", fields)

    @skip("Appears fields is maybe cached?")
    def test_get_fields_superuser(self):
        """If superuser then country_override stays"""
        self.request.user = self.superuser
        self.assertTrue(self.request.user.is_superuser)
        fields = self.admin.get_fields(self.request)
        self.assertIn("country_override", fields)

    def test_save_model_supervisor(self):
        """If supervisor provided, then set supervisor"""
        mock_form = Mock()
        mock_form.data = {"supervisor": self.superuser.pk}
        obj = ProfileFactory()
        self.assertIsNone(obj.supervisor)
        self.admin.save_model(
            self.request,
            obj,
            mock_form,
            None)
        profile_updated = UserProfile.objects.get(pk=obj.pk)
        self.assertEqual(profile_updated.supervisor, self.superuser)

    def test_save_model_oic(self):
        """If OIC provided, then set OIC"""
        mock_form = Mock()
        mock_form.data = {"oic": self.superuser.pk}
        obj = ProfileFactory()
        self.assertIsNone(obj.oic)
        self.admin.save_model(
            self.request,
            obj,
            mock_form,
            None)
        profile_updated = UserProfile.objects.get(pk=obj.pk)
        self.assertEqual(profile_updated.oic, self.superuser)


class TestUserAdminPlus(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        site = AdminSite()
        cls.admin = UserAdminPlus(User, site)
        cls.request = MockRequest()
        cls.superuser = UserFactory(is_superuser=True)
        cls.user = UserFactory()

    def test_office(self):
        self.assertEqual(
            self.admin.office(self.user),
            self.user.profile.office
        )

    def test_has_add_permission(self):
        self.assertFalse(self.admin.has_add_permission(self.request))

    def test_has_delete_permission(self):
        self.assertFalse(self.admin.has_delete_permission(self.request))

    def test_get_readonly_fields(self):
        """If user NOT superuser then is_superuser is readonly"""
        self.request.user = self.user
        readonly_fields = self.admin.get_readonly_fields(self.request)
        self.assertIn("is_superuser", readonly_fields)

    def test_get_readonly_fields_superuser(self):
        """If user is superuser then is_superuser is NOT readonly"""
        self.request.user = self.superuser
        self.assertTrue(self.request.user.is_superuser)
        readonly_fields = self.admin.get_readonly_fields(self.request)
        self.assertNotIn("is_superuser", readonly_fields)


class TestCountryAdmin(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        site = AdminSite()
        cls.admin = CountryAdmin(Country, site)
        cls.request = MockRequest()
        cls.superuser = UserFactory(is_superuser=True, is_staff=True)

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_has_add_permission(self):
        self.assertFalse(self.admin.has_add_permission(self.request))

    def test_update_hact_button_on_change_page(self):
        country = Country.objects.exclude(schema_name='public').first()
        url = reverse('admin:users_country_change', args=[country.pk])
        response = self.client.get(url)
        self.assertContains(response, text=">Update HACT<", msg_prefix=response.content.decode('utf-8'))
        self.assertTemplateUsed('admin/users/country/change_form.html')

    def test_update_hact_action_nonpublic_country(self):
        country = Country.objects.exclude(schema_name='public').first()
        url = reverse('admin:users_country_update_hact', args=[country.pk])
        with patch.object(update_hact_for_country, 'delay') as mock_delay:
            with patch.object(messages, 'info') as mock_info:
                response = self.client.get(url)
        self.assertRedirects(response, reverse('admin:users_country_change', args=[country.pk]))
        mock_delay.assert_called()
        mock_info.assert_called_with(ANY, "HACT update has been started for %s" % country.name)

    def test_update_hact_action_public_country(self):
        country = Country.objects.filter(schema_name='public').first()
        if country is None:
            country = Country.objects.first()
            country.schema_name = 'public'
            with schema_context('public'):
                country.save()
            country.refresh_from_db()
            self.assertEqual(country.schema_name, 'public')
        url = reverse('admin:users_country_update_hact', args=[country.pk])
        with patch('etools.applications.users.admin.update_hact_values') as mock_update:
            with patch.object(messages, 'info') as mock_info:
                response = self.client.get(url)
        self.assertRedirects(response, reverse('admin:users_country_change', args=[country.pk]))
        mock_info.assert_called_with(ANY, "HACT update has been scheduled for all countries")
        mock_update.assert_called()
