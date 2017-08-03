import datetime
import sys

from EquiTrack.settings.base import *  # noqa


ALLOWED_HOSTS = ['127.0.0.1']
DEBUG = True

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
        # Send email to console for local dev
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
