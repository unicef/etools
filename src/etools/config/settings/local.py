import logging
import sys

from etools.config.settings.base import *  # noqa: F403

ALLOWED_HOSTS = ['*']
DEBUG = True
CELERY_TASK_ALWAYS_EAGER = True

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

# No Redis for local dev.
# Use custom locmemcache to add have .keys functionality
CACHES = {
    'default': {
        'BACKEND': 'etools.libraries.locmemcache.base.eToolsLocMemCache',
    }
}

# local override for django-cors-headers
CORS_ORIGIN_ALLOW_ALL = True

if 'test' in sys.argv:
    # Settings for automated tests

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

# Optional for debugging db queries
# MIDDLEWARE += ('etools.applications.core.middleware.QueryCountDebugMiddleware',)
