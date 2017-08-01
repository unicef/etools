import datetime
import sys

from EquiTrack.settings.base import *  # noqa


# ######### DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1']

# ######### END DEBUG CONFIGURATION

CELERY_ALWAYS_EAGER = True


JWT_AUTH = {
   'JWT_ENCODE_HANDLER':
   'rest_framework_jwt.utils.jwt_encode_handler',

   'JWT_DECODE_HANDLER':
   'rest_framework_jwt.utils.jwt_decode_handler',

   'JWT_PAYLOAD_HANDLER':
   'rest_framework_jwt.utils.jwt_payload_handler',

   'JWT_PAYLOAD_GET_USER_ID_HANDLER':
   'rest_framework_jwt.utils.jwt_get_user_id_from_payload_handler',

   'JWT_PAYLOAD_GET_USERNAME_HANDLER':
   'rest_framework_jwt.utils.jwt_get_username_from_payload_handler',

   'JWT_RESPONSE_PAYLOAD_HANDLER':
   'rest_framework_jwt.utils.jwt_response_payload_handler',

   # 'JWT_SECRET_KEY': JWT_SECRET_KEY,
   'JWT_SECRET_KEY': 'ssdfsdfsdfsd',
   # 'JWT_ALGORITHM': 'RS256',
   'JWT_ALGORITHM': 'HS256',
   'JWT_VERIFY': True,
   'JWT_VERIFY_EXPIRATION': True,
   'JWT_LEEWAY': 30,
   'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=30000),
   # 'JWT_AUDIENCE': 'https://etools-staging.unicef.org/API',
   'JWT_AUDIENCE': None,
   'JWT_ISSUER': None,

   'JWT_ALLOW_REFRESH': False,
   'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),

   'JWT_AUTH_HEADER_PREFIX': 'JWT',
}

POST_OFFICE = {
    'DEFAULT_PRIORITY': 'now',
    'BACKENDS': {
        # Will ensure email is sent async
        'default': 'django.core.mail.backends.console.EmailBackend'
    }
}


if 'test' in sys.argv:
    # Settings for automated tests

    # All mail sent out through this backend is stored at django.core.mail.outbox
    # https://docs.djangoproject.com/en/1.9/topics/email/#in-memory-backend
    POST_OFFICE['BACKENDS']['default'] = 'django.core.mail.backends.locmem.EmailBackend'

    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]
    TEST_RUNNER = 'EquiTrack.tests.runners.TestRunner'
else:
    # Settings which should NOT be active during automated tests

    # ######### TOOLBAR CONFIGURATION
    # See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    INSTALLED_APPS += (  # noqa
        'debug_toolbar',
        'django_extensions',
    )

    # See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    INTERNAL_IPS = ('127.0.0.1',)

    # See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    MIDDLEWARE_CLASSES += (  # noqa
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

    # See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        'SHOW_TEMPLATE_CONTEXT': True,
    }
    # ######### END TOOLBAR CONFIGURATION
