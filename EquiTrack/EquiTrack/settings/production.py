"""Production settings and globals."""
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

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

# production overrides for django-rest-framework-jwt
certificate_text = open(join(DJANGO_ROOT, 'saml/etripspub.cer'), 'r').read()
certificate = load_pem_x509_certificate(certificate_text, default_backend())
JWT_SECRET_KEY = certificate.public_key()
JWT_AUTH.update({
    'JWT_SECRET_KEY': JWT_SECRET_KEY,
    'JWT_ALGORITHM': 'RS256',
    'JWT_LEEWAY': 60,
    'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=3000),
    # TODO: FIX THIS, NEEDS SETUP WITH ADFS
    'JWT_AUDIENCE': 'https://etools.unicef.org/API',
})
