
from django.core.management import call_command
from django.db import connection

from django.test import TestCase

from rest_framework.test import APIRequestFactory, APIClient, force_authenticate

from tenant_schemas.utils import get_tenant_model
from tenant_schemas.utils import get_public_schema_name




class APITenantTestCase(TestCase):
    client_class = APIClient

    def forced_auth_req(self, method, url, handler, user=None, data={}):
        factory = self.factory()
        view = handler.as_view()
        req_to_call = getattr(factory, method)
        request = req_to_call(url, data)
        user = user if user else self.user
        force_authenticate(request, user=user)
        return view(request)

    @classmethod
    def setUpClass(cls):
        cls.factory = APIRequestFactory
        cls.sync_shared()
        tenant_domain = 'tenant.test.com'
        cls.tenant = get_tenant_model()(domain_url=tenant_domain, schema_name='test', name="Test Country")
        cls.tenant.save(verbosity=0)  # todo: is there any way to get the verbosity from the test command here?
        connection.set_tenant(cls.tenant)


    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.tenant.delete()

        cursor = connection.cursor()
        cursor.execute('DROP SCHEMA test CASCADE')

    @classmethod
    def sync_shared(cls):
        call_command('migrate_schemas',
                     schema_name=get_public_schema_name(),
                     interactive=False,
                     verbosity=0)
