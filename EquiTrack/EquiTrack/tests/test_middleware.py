
from unittest import skip

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.test import TestCase, RequestFactory, override_settings

from EquiTrack.middleware import EToolsTenantMiddleware, ANONYMOUS_ALLOWED_URL_FRAGMENTS
from users.tests.factories import CountryFactory, UserFactory


class EToolsTenantMiddlewareTest(TestCase):
    request_factory = RequestFactory()

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.request = self.request_factory.get('/')
        self.request.user = self.user
        self.inactive_workspace_url = reverse('workspace-inactive')

    def test_no_user_return_none(self):
        "If no user, allow them to pass."
        self.request.user = None
        self.assertEquals(EToolsTenantMiddleware().process_request(self.request), None)

    def test_inactive_workspace_return_none(self):
        "If trying to access an inactive workspace, middleware returns None."
        # use an AnonymousUser because we know this user should be redirected to login, if this test
        # were to fail
        self.request.user = AnonymousUser()
        self.request.path = self.inactive_workspace_url
        self.assertEquals(EToolsTenantMiddleware().process_request(self.request), None)

    def test_anonymous_user_allowed_urls(self):
        "If AnonymousUser tries to access these URLs, middleware returns None, allowing them to pass."
        allowed_url_paths = ANONYMOUS_ALLOWED_URL_FRAGMENTS
        self.request.user = AnonymousUser()
        for path in allowed_url_paths:
            self.request.path = '/{}'.format(path)
            self.assertEquals(EToolsTenantMiddleware().process_request(self.request), None)

    def test_anonymous_user_redirects_to_login(self):
        "If AnonymousUser tries to access any other URLs, middleware redirects them to login."
        self.request.user = AnonymousUser()
        response = EToolsTenantMiddleware().process_request(self.request)
        self.assertRedirects(response, settings.LOGIN_URL, fetch_redirect_response=False)

    def test_user_without_country_redirects_to_inactive_workspace(self):
        "If user has no country, middleware redirects them to inactive workspace."
        self.request.user.profile.country = None
        response = EToolsTenantMiddleware().process_request(self.request)
        self.assertRedirects(response, self.inactive_workspace_url, fetch_redirect_response=False)

    def test_superuser_without_country_return_none(self):
        "Superuser without country is allowed to pass."
        superuser = UserFactory(is_superuser=True, profile__country=None)
        self.request.user = superuser
        self.assertEquals(EToolsTenantMiddleware().process_request(self.request), None)

    @skip('unused')
    @override_settings(INACTIVE_BUSINESS_AREAS=['ZZZ'])
    def test_user_with_inactive_country_redirects_to_inactive_workspace(self):
        "If user is part of an inactive workspace, redirect to inactive workspace."
        response = EToolsTenantMiddleware().process_request(self.request)
        self.assertRedirects(response, self.inactive_workspace_url, fetch_redirect_response=False)

    @override_settings(INACTIVE_BUSINESS_AREAS=['ZZZ'])
    def test_superuser_inactive_country_return_none(self):
        "Superuser in inactive workspace is allowed to pass."
        superuser = UserFactory(is_superuser=True)
        self.request.user = superuser
        self.assertEquals(EToolsTenantMiddleware().process_request(self.request), None)

    @override_settings(PUBLIC_SCHEMA_URLCONF='foo')
    def test_public_schema_urlconf(self):
        """
        This just tests a code path that was copied from the django-tenant-schemas middleware when we
        copy/pasted. eTools does not use it.
        """
        country = CountryFactory(schema_name='public', domain_url='public.example.com')
        superuser = UserFactory(is_superuser=True, profile__country=country)
        self.request.user = superuser
        EToolsTenantMiddleware().process_request(self.request)
        self.assertEqual(self.request.urlconf, 'foo')
