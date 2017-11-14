import logging
import sys

from EquiTrack.settings.base import *  # noqa: F403

DEBUG = True
CELERY_ALWAYS_EAGER = True

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
    'EquiTrack.mixins.CsrfExemptSessionAuthentication',
) + REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']

# No SAML for local dev
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

# No Redis for local dev
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# local override for django-allauth
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

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
        'utils.common',
        'utils.writable_serializers',
    ]

    # Disable logging output during tests
    logging.disable(logging.CRITICAL)
else:
    # Settings which should NOT be active during automated tests

    # django-debug-toolbar: https://django-debug-toolbar.readthedocs.io/en/stable/configuration.html
    INSTALLED_APPS += (  # noqa
        'debug_toolbar',
        'django_extensions',
    )
    INTERNAL_IPS = ('127.0.0.1',)
    MIDDLEWARE_CLASSES += (  # noqa
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        'SHOW_TEMPLATE_CONTEXT': True,
    }

LOGGING = LOGGING  # noqa - just here for flake purposes. should be imported from EquiTrack.settings.base
# log updates for more info in local environment
LOGGING['disable_existing_loggers'] = False  # don't disable any existing loggers

# enable tenant logging http://django-tenant-schemas.readthedocs.io/en/latest/use.html#logging
LOGGING['filters'] = {
    'tenant_context': {
        '()': 'tenant_schemas.log.TenantContextFilter'
    }
}
LOGGING['formatters'] = {
    'tenant_context': {
        'format': '[%(schema_name)s:%(domain_url)s] '
        '%(levelname)-7s %(asctime)s %(message)s',
    },
}
LOGGING['handlers']['console']['filters'] = ['tenant_context']
LOGGING['handlers']['console']['formatter'] = 'tenant_context'
