from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.db import connection
from tenant_schemas.test.cases import TenantTestCase
from tenant_schemas.utils import get_tenant_model

from users.models import WorkspaceCounter


TENANT_DOMAIN = 'tenant.test.com'
SCHEMA_NAME = 'test'


class EToolsTenantTestCase(TenantTestCase):
    """
    Faster version of TenantTestCase.  (Based on FastTenantTestCase
    provided by django-tenant-schemas.)
    """

    def _should_check_constraints(self, connection):
        # We have some tests that fail the constraint checking after each test
        # added in Django 1.10. Disable that for now.
        return False

    @classmethod
    def _load_fixtures(cls):
        '''
        Load fixtures for current connection (shared/public or tenant)

        This works the same as the code in TestCase.setUpClass(), but is
        broken out here so we can call it twice, once for the public schema
        and once for the tenant schema.

        '''
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

    @classmethod
    def setUpClass(cls):
        # This replaces TestCase.setUpClass so that we can do some setup in
        # different schemas.
        # It also drops the check whether the database supports transactions.
        cls.sync_shared()

        TenantModel = get_tenant_model()
        try:
            cls.tenant = TenantModel.objects.get(domain_url=TENANT_DOMAIN, schema_name=SCHEMA_NAME)
        except:
            cls.tenant = TenantModel(domain_url=TENANT_DOMAIN, schema_name=SCHEMA_NAME)
            cls.tenant.save(verbosity=0)

        cls.tenant.business_area_code = 'ZZZ'
        cls.tenant.save(verbosity=0)

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
