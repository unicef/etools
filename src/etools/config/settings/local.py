import logging
import sys

from etools.config.settings.base import *  # noqa: F403

ALLOWED_HOSTS = ['*']
DEBUG = True
CELERY_TASK_ALWAYS_EAGER = True

# python manage.py migrate_schemas --executor=multiprocessing
TENANT_MULTIPROCESSING_MAX_PROCESSES = int(get_from_secrets_or_env('TENANT_MULTIPROCESSING_MAX_PROCESSES', 30))

REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += (
    'etools.applications.core.auth.DRFBasicAuthMixin',
)

POST_OFFICE = {
    'DEFAULT_PRIORITY': 'now',
    'BACKENDS': {
        # Send email to console for local dev
        'default': 'django.core.mail.backends.console.EmailBackend'
    }
}


# change config to remove CSRF verification in localhost in order to enable testing from postman.
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = (
    # this setting fixes the bug where user can be logged in as AnonymousUser
    'etools.applications.core.auth.CsrfExemptSessionAuthentication',
    'rest_framework.authentication.BasicAuthentication',
) + REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']

AUTHENTICATION_BACKENDS = (
    # 'social_core.backends.azuread_b2c.AzureADB2COAuth2',
    'etools.applications.core.auth.CustomAzureADBBCOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

# No Redis for local dev
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# local override for django-cors-headers
CORS_ORIGIN_ALLOW_ALL = True

if 'test' in sys.argv:
    # Settings for automated tests - tblib needs to be installed for pickling support on parallel tests:
    #
    sys.path.append('/pythonlibs/external')
    print("sys.path is set")
    # TODO: find a better way for the following
    # if running in parallel, the clones migrations will not be updated, if so:
    if '--keepdb' not in sys.argv and any("--parallel" in arg for arg in sys.argv):
        from django.db import connection
        c = connection.cursor()
        for i in range(0, TENANT_MULTIPROCESSING_MAX_PROCESSES):
            c.execute('''DROP DATABASE IF EXISTS test_etools_{};'''.format(i))
        # you can delete manually by running the output of the following sql
        # select concat('drop database "', datname, '";' ) from pg_database where datname like 'test_etools%';
        raise Exception("If you're trying to run in parallel, in order to avoid issues, it's reccomended that you run"
                        " with keep db partially on a single thread until the migrations are run, then run with keepdb"
                        " in parallel - if you're trying something else - comment me out")

    # All mail sent out through this backend is stored at django.core.mail.outbox
    # https://docs.djangoproject.com/en/1.9/topics/email/#in-memory-backend
    POST_OFFICE['BACKENDS']['default'] = 'django.core.mail.backends.locmem.EmailBackend'

    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]

    TEST_NON_SERIALIZED_APPS = [
        # These apps contains test models that haven't been created by migration.
        # So on the serialization stage these models do not exist.
        'etools.applications.permissions2',
    ]

    # Disable logging output during tests
    logging.disable(logging.CRITICAL)
elif 'runserver' in sys.argv or 'shell_plus' in sys.argv:
    # Settings which should only be active when running a local server

    # django-debug-toolbar: https://django-debug-toolbar.readthedocs.io/en/stable/configuration.html
    INSTALLED_APPS += (  # noqa
        'debug_toolbar',
    )
    INTERNAL_IPS = ('127.0.0.1',)
    MIDDLEWARE += (  # noqa
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TEMPLATE_CONTEXT': True,
    }

LOGGING = LOGGING  # noqa - just here for flake purposes. should be imported from etools.config.settings.base
# log updates for more info in local environment
LOGGING['disable_existing_loggers'] = False  # don't disable any existing loggers

# https://django-tenants.readthedocs.io/en/latest/use.html#logging
LOGGING['filters'] = {
    'tenant_context': {
        '()': 'django_tenants.log.TenantContextFilter'
    },
}
LOGGING['formatters'] = {
    'tenant_context': {
        'format': '[%(schema_name)s:%(name)s] '
        '%(levelname)-7s %(asctime)s %(message)s',
    },
}
LOGGING['loggers'] = {'django.db': {}}
LOGGING['handlers']['console']['filters'] = ['tenant_context']
LOGGING['handlers']['console']['formatter'] = 'tenant_context'

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

if os.path.isfile(join(CONFIG_ROOT, 'keys/jwt/key.pem')):
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.x509 import load_pem_x509_certificate
    private_key_bytes = open(join(CONFIG_ROOT, 'keys/jwt/key.pem'), 'rb').read()  # noqa: F405
    public_key_bytes = open(join(CONFIG_ROOT, 'keys/jwt/certificate.pem'), 'rb').read()  # noqa: F405

    JWT_PRIVATE_KEY = serialization.load_pem_private_key(private_key_bytes, password=None,
                                                         backend=default_backend())

    certificate = load_pem_x509_certificate(public_key_bytes, default_backend())
    JWT_PUBLIC_KEY = certificate.public_key()

    SIMPLE_JWT.update({  # noqa: F405
        'SIGNING_KEY': JWT_PRIVATE_KEY,
        'VERIFYING_KEY': JWT_PUBLIC_KEY,
        'AUDIENCE': 'https://etools.unicef.org/',
        'ALGORITHM': 'RS256',
    })

# Optional for debugging db queries
# MIDDLEWARE += ('etools.applications.core.middleware.QueryCountDebugMiddleware',)
