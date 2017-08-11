"""Production settings and globals."""

from os import environ
from base import *

# raven (Sentry): https://github.com/getsentry/raven-python
RAVEN_CONFIG = {
    'dsn': environ.get('SENTRY_DSN', None),
}
INSTALLED_APPS += (  # noqa
    'raven.contrib.django.raven_compat',
)

SECRET_KEY = os.environ["SECRET_KEY"]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'


LOGIN_URL = '/login/'

########## JWT AUTH CONFIGURATION
certificate_text = open(join(DJANGO_ROOT, 'saml/etripspub.cer'), 'r').read()
certificate = load_pem_x509_certificate(certificate_text, default_backend())
JWT_SECRET_KEY = certificate.public_key()
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

    'JWT_SECRET_KEY': JWT_SECRET_KEY,
    'JWT_ALGORITHM': 'RS256',
    'JWT_VERIFY': True,
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_LEEWAY': 60,
    'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=3000),
    #'JWT_AUDIENCE': 'https://{}/API'.format(HOST),
    # TODO: FIX THIS, NEEDS SETUP WITH ADFS
    'JWT_AUDIENCE': 'https://etools.unicef.org/API',
    'JWT_ISSUER': None,

    'JWT_ALLOW_REFRESH': False,
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),

    'JWT_AUTH_HEADER_PREFIX': 'JWT',
}
######## END JWT AUTH CONFIGURATION
