import os

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.db import connection
from django.urls import resolve

from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_domain_model, get_tenant_model
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from unicef_notification.models import EmailTemplate

from etools.applications.users.models import WorkspaceCounter
from etools.applications.users.tests.factories import SCHEMA_NAME

TENANT_DOMAIN = 'tenant.test.com'


class BaseTenantTestCase(TenantTestCase):
    """
    Faster version of TenantTestCase.  (Based on FastTenantTestCase provided by django-tenants.)
    """
    client_class = APIClient
    maxDiff = None

    def _should_check_constraints(self, connection):
        # We have some tests that fail the constraint checking after each test
        # added in Django 1.10. Disable that for now.
        return False

    @classmethod
    def _load_fixtures(cls):
        """
        Load fixtures for current connection (shared/public or tenant)

        This works the same as the code in TestCase.setUpClass(), but is
        broken out here so we can call it twice, once for the public schema
        and once for the tenant schema.

        """
        if cls.fixtures:
            for db_name in cls._databases_names(include_mirrors=False):
                try:
                    call_command('loaddata', *cls.fixtures, **{
                                 'verbosity': 0,
                                 'database': db_name,
                                 })
                except Exception:
                    cls._rollback_atomics(cls.cls_atomics)
                    raise

    @classmethod
    def setUpClass(cls):
        # This replaces TestCase.setUpClass so that we can do some setup in
        # different schemas.
        # It also drops the check whether the database supports transactions.
        cls.sync_shared()

        EmailTemplate.objects.get_or_create(name='audit/staff_member/invite')
        EmailTemplate.objects.get_or_create(name='audit/engagement/submit_to_auditor')

        TenantModel = get_tenant_model()
        cls.tenant, _ = TenantModel.objects.get_or_create(schema_name=SCHEMA_NAME, defaults={
            'business_area_code': 'ZZZ',
            'country_short_code': 'TST'
        })
        cls.domain = get_tenant_domain_model().objects.get_or_create(domain=TENANT_DOMAIN, tenant=cls.tenant)
        # cls.public = TenantModel.objects.get_or_create(schema_name='public', business_area_code='ABC', name='UNICEF')
        settings.STATIC_ROOT = os.path.join(settings.PACKAGE_ROOT, 'assets')
        try:
            cls.tenant.counters
        except ObjectDoesNotExist:
            WorkspaceCounter.objects.create(workspace=cls.tenant)

        cls.cls_atomics = cls._enter_atomics()

        # Load fixtures for shared schema
        cls._load_fixtures()

        connection.set_tenant(cls.tenant)

        # Load fixtures for tenant schema
        cls._load_fixtures()

        try:
            cls.setUpTestData()
        except Exception:
            cls._rollback_atomics(cls.cls_atomics)
            raise

    @classmethod
    def tearDownClass(cls):
        cls._rollback_atomics(cls.cls_atomics)
        connection.set_schema_to_public()

    def assertKeysIn(self, keys, container, msg=None, exact=False):
        """Small helper to check all keys in the response payload"""
        key_set = set(keys)
        container_set = set(container)
        missing_keys = key_set - container_set
        if missing_keys:
            self.fail('Missing keys: {}'.format(', '.join(missing_keys)))

        if exact and len(key_set) != len(container_set):
            self.fail('{} != {}'.format(', '.join(key_set), ', '.join(container_set)))

    def forced_auth_req(self, method, url, user=None, data=None, request_format='json', **kwargs):
        """
        Function that allows api methods to be called with forced authentication

        If `user` parameter not provided, then `self.user` will be used

        If `view` parameter is provided, then the `view` function
        will be called directly, otherwise `url` will be resolved
        """
        factory = APIRequestFactory()

        if data is None:
            data = {}

        req_to_call = getattr(factory, method)
        request = req_to_call(url, data, format=request_format, **kwargs)
        if hasattr(user, "profile") and user.profile.country:
            request.tenant = user.profile.country

        user = user or self.user
        request.user = user if user else AnonymousUser()
        force_authenticate(request, user=user)

        if "view" in kwargs:
            view = kwargs.pop("view")
            response = view(request)
        else:
            view_info = resolve(url)
            view = view_info.func
            response = view(request, *view_info.args, **view_info.kwargs)

        if hasattr(response, 'render'):
            response.render()

        return response
