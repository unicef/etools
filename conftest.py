import pytest


def pytest_configure(config):
    from django.conf import settings
    settings.INSTALLED_APPS = settings.INSTALLED_APPS + (
        'etools.applications.utils.permissions.tests',
        'etools.applications.permissions2.tests',
        'etools.applications.utils.common.tests.test_utils',
    )
    settings.POST_OFFICE = {
        'DEFAULT_PRIORITY': 3,
        'LOG_LEVEL': 2,  # Log only failed deliveries
        'BACKENDS': {
            # Send email to console for local dev
            'default': 'django.core.mail.backends.locmem.EmailBackend'
        }
    }
    settings.TEST_NON_SERIALIZED_APPS = [
        # These apps contains test models that haven't been created by migration.
        # So on the serialization stage these models do not exist.
        'etools.applications.utils.permissions.tests',
        'etools.applications.utils.common',
        'etools.applications.utils.writable_serializers',
    ]

    settings.PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]


@pytest.fixture(autouse=True, scope='session')
def django_db_setup(django_db_modify_db_settings, django_db_keepdb, django_db_createdb, django_db_use_migrations, django_db_blocker):
    from tenant_schemas.migration_executors import get_executor
    from tenant_schemas.utils import get_public_schema_name, get_tenant_model
    if not django_db_keepdb or django_db_createdb:
        with django_db_blocker.unblock():
            executor = get_executor(codename=None)([], {'no_color': False, 'verbosity': 1,
                                                        'interactive': False,
                                                        'app_label': None,
                                                        'fake': False,
                                                        'fake_initial': False,
                                                        'run_syncdb': True,
                                                        'database': 'default'})
            executor.run_migrations(tenants=[get_public_schema_name()])
            tenants = get_tenant_model().objects.exclude(schema_name=get_public_schema_name()).values_list(
                'schema_name', flat=True)
            executor.run_migrations(tenants=tenants)
