from django.core.urlresolvers import resolve
from django.http.response import HttpResponse

from rest_framework.test import APIClient, force_authenticate, APIRequestFactory

from tenant_schemas.test.cases import TenantTestCase
from tenant_schemas.test.client import TenantClient

from django.db import connection
from django.core.management import call_command
from tenant_schemas.utils import get_tenant_model


class FastTenantTestCase(TenantTestCase):

    @classmethod
    def setUpClass(cls):
        cls.sync_shared()
        tenant_domain = 'tenant.test.com'

        TenantModel = get_tenant_model()
        try:
            cls.tenant = TenantModel.objects.get(domain_url=tenant_domain, schema_name='test')
        except:
            cls.tenant = TenantModel(domain_url=tenant_domain, schema_name='test')
            cls.tenant.save(verbosity=0)

        connection.set_tenant(cls.tenant)

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
        connection.set_schema_to_public()

class APITenantClient(TenantClient, APIClient):
    def __init__(self, tenant, **defaults):
        super(APITenantClient, self).__init__(tenant=tenant, defaults=defaults)


class APITenantTestCase(FastTenantTestCase):
    """
    Base test case for testing APIs
    """
    client_class = APIClient

    def forced_auth_req(self, method, url, user=None, data=None, **kwargs):
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
        request = req_to_call(url, data, format='json', **kwargs)

        user = user or self.user
        force_authenticate(request, user=user)

        response = view(request, *view_info.args, **view_info.kwargs)
        if hasattr(response, 'render'):
            response.render()

        return response
