from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.core.urlresolvers import resolve, reverse, NoReverseMatch
from django.db import connection
from rest_framework.test import APIClient, force_authenticate, APIRequestFactory
from tenant_schemas.test.cases import TenantTestCase
from tenant_schemas.utils import get_tenant_model

from users.models import WorkspaceCounter


def _delimit_namespace(namespace):
    '''Add delimiter (':') to namespace if necessary'''
    if namespace and not namespace.endswith(':'):
        namespace += ':'

    return namespace


class URLAssertionMixin(object):
    '''Mixin for any class derived from unittest.TestCase. Provides some assertion helpers for testing URL patterns'''

    def assertReversal(self, names_and_paths, namespace, url_prefix):
        '''Assert that all URLs in names_and_paths reverse as expected.

        names_and_paths should be a list/tuple of 3-tuples of (URL pattern name, URL suffix, kwargs), e.g. --
            (('intervention-list', '', {}),
             ('intervention-list-dash', 'dash/', {}),
             ('intervention-detail', '1/', {'pk': 1}), )

        namespace should be the invariant namespace for reversal, e.g. 'partners_api'

        url_prefix should be the invariant part of the expected URL, e.g. '/api/v2/interventions/'

        Using the examples above, this --
            reverse('partners_api:intervention-detail', {'pk': 1})
        will be compared to this --
            '/api/v2/interventions/1/'
        '''
        namespace = _delimit_namespace(namespace)

        for name, url_suffix, kwargs in names_and_paths:
            actual_url = reverse(namespace + name, kwargs=kwargs)
            expected_url = url_prefix + url_suffix
            self.assertEqual(actual_url, expected_url)

    def assertIntParamRegexes(self, names_and_paths, namespace):
        '''Assert that all URLs in names_and_paths that take int keyword args reject non-int args. non-int kwargs in
        URL patterns are ignored.

        See assertReversal() for an explanation of parameters.

        Limitation: int kwargs must be passed to this function as ints, not strings. Ints passed as strings won't be
        tested. For example --
        Correct:   {'pk': 1}
        Incorrect: {'pk': '1'}
        '''
        namespace = _delimit_namespace(namespace)

        # First, filter out patterns that don't use kwargs.
        names_and_paths = [(name, url_part, kwargs) for name, url_part, kwargs in names_and_paths if kwargs]

        # First, ensure these are reversible when given accetpable params. This ensures that when when NoReverseMatch
        # is raised below, it's raised for the right reason (param rejection) rather than for something that's not
        # being tested (e.g. incorrect namespace).
        for name, url_part, kwargs in names_and_paths:
            reverse(namespace + name, kwargs=kwargs)

        for invalid_value in (None, 'a', 'abc', '0x99', '-99'):
            for name, url_part, kwargs in names_and_paths:
                # Replace kwargs with a dict in which each int value is the invalid int.
                kwargs = {key: invalid_value for key, value in kwargs.items() if isinstance(value, int)}
                # The try/except below allows us to give an informative AssertionError. In Python 3, this can be
                # replaced with `with self.assertRaises(NoReverseMatch, msg=fail_msg):`
                try:
                    reverse(namespace + name, kwargs=kwargs)
                except NoReverseMatch:
                    # This is what we hope will happen.
                    pass
                else:
                    fail_msg = 'NoReverseMatch not raised for namespace={}, kwargs={}'.format(namespace + name, kwargs)
                    raise AssertionError(fail_msg)


class FastTenantTestCase(TenantTestCase):

    @classmethod
    def setUpClass(cls):
        cls.sync_shared()
        tenant_domain = 'tenant.test.com'

        TenantModel = get_tenant_model()
        try:
            cls.tenant = TenantModel.objects.get(domain_url=tenant_domain, schema_name='test')
        except TenantModel.DoesNotExist:
            cls.tenant = TenantModel(domain_url=tenant_domain, schema_name='test')
            cls.tenant.save(verbosity=0)

        cls.tenant.business_area_code = 'ZZZ'
        cls.tenant.save(verbosity=0)

        try:
            cls.tenant.counters
        except ObjectDoesNotExist:
            WorkspaceCounter.objects.create(workspace=cls.tenant)

        connection.set_tenant(cls.tenant)

        cls.cls_atomics = cls._enter_atomics()

        if cls.fixtures:
            for db_name in cls._databases_names(include_mirrors=False):
                    try:
                        call_command('loaddata', *cls.fixtures, **{
                            'verbosity': 0,
                            'commit': False,
                            'database': db_name,
                        })
                    except Exception:
                        cls._rollback_atomics(cls.cls_atomics)
                        raise
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


class APITenantTestCase(FastTenantTestCase):
    """
    Base test case for testing APIs
    """
    client_class = APIClient
    maxDiff = None

    def forced_auth_req(self, method, url, user=None, data=None, request_format='json', **kwargs):
        """
        Function that allows api methods to be called with forced authentication

        :param method: the HTTP method 'get'/'post'
        :type method: str
        :param url: the relative url to the base domain
        :type url: st
        :param user: optional user if not authenticated as the current user
        :type user: django.contrib.auth.models.User
        :param data: any data that should be passed to the API view
        :type data: dict
        """
        factory = APIRequestFactory()
        view_info = resolve(url)

        data = data or {}
        view = view_info.func
        req_to_call = getattr(factory, method)
        request = req_to_call(url, data, format=request_format, **kwargs)

        user = user or self.user
        force_authenticate(request, user=user)

        response = view(request, *view_info.args, **view_info.kwargs)
        if hasattr(response, 'render'):
            response.render()

        return response


class WorkspaceRequiredAPITestMixIn(object):
    """
    For APITenantTestCases that have a required workspace param, just automatically
    set the current tenant.
    """
    def forced_auth_req(self, method, url, user=None, data=None, request_format='json', **kwargs):
        data = data or {}
        data['workspace'] = self.tenant.business_area_code
        return super(WorkspaceRequiredAPITestMixIn, self).forced_auth_req(
            method, url, user=user, data=data, request_format=request_format, **kwargs
        )
