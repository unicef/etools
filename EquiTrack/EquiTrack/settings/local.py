import datetime
import sys

from EquiTrack.settings.base import *  # noqa


DEBUG = True

CELERY_ALWAYS_EAGER = True


POST_OFFICE = {
    'DEFAULT_PRIORITY': 'now',
    'BACKENDS': {
        # Send email to console for local dev
        'default': 'django.core.mail.backends.console.EmailBackend'
    }
}

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

# django-allauth: https://github.com/pennersr/django-allauth
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

# django-cors-headers: https://github.com/ottoyiu/django-cors-headers
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
