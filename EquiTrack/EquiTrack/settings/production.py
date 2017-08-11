"""Production settings and globals."""
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

from base import *  # noqa: F403

# raven (Sentry): https://github.com/getsentry/raven-python
RAVEN_CONFIG = {
    'dsn': os.environ.get('SENTRY_DSN'),  # noqa: F405
}
# Override default client, in order to send extra data to Sentry
SENTRY_CLIENT = 'utils.sentry.client.EToolsSentryClient'
INSTALLED_APPS += (  # noqa: F405
    'raven.contrib.django.raven_compat',
)

# Security settings for production
SECRET_KEY = os.environ["SECRET_KEY"]  # noqa: F405
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# production overrides for django-rest-framework-jwt
certificate_text = open(join(DJANGO_ROOT, 'saml/etripspub.cer'), 'r').read()  # noqa: F405
certificate = load_pem_x509_certificate(certificate_text, default_backend())
JWT_SECRET_KEY = certificate.public_key()
JWT_AUTH.update({  # noqa: F405
    'JWT_SECRET_KEY': JWT_SECRET_KEY,
    'JWT_ALGORITHM': 'RS256',
    'JWT_LEEWAY': 60,
    'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=3000),  # noqa: F405
    # TODO: FIX THIS, NEEDS SETUP WITH ADFS
    'JWT_AUDIENCE': 'https://etools.unicef.org/API',
})
