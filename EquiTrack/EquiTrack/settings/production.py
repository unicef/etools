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
ALLOWED_HOSTS = [
    # Nope, regular expressions are not supported for this setting
    'etools.unicef.org',
    'etools-demo.unicef.org',
    'etools-dev.unicef.org',
    'etools-staging.unicef.org',
    'etools-test.unicef.org',
]
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

# django-storages: https://django-storages.readthedocs.io/en/latest/backends/azure.html
AZURE_ACCOUNT_NAME = os.environ.get('AZURE_ACCOUNT_NAME')
AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY')
AZURE_CONTAINER = os.environ.get('AZURE_CONTAINER')
AZURE_SSL = True
AZURE_AUTO_SIGN = True  # flag for automatically signing urls
AZURE_ACCESS_POLICY_EXPIRY = 120  # length of time before signature expires in seconds
AZURE_ACCESS_POLICY_PERMISSION = 'r'  # read permission

if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY and AZURE_CONTAINER:
    DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
    from storages.backends.azure_storage import AzureStorage
    storage = AzureStorage()
    with storage.open('saml/certs/saml.key') as key, \
            storage.open('saml/certs/sp.crt') as crt, \
            storage.open('saml/federationmetadata.xml') as meta:
        with open('EquiTrack/saml/certs/saml.key', 'w+') as new_key, \
                open('EquiTrack/saml/certs/sp.crt', 'w+') as new_crt, \
                open('EquiTrack/saml/federationmetadata.xml', 'w+') as new_meta:
            new_key.write(key.read())
            new_crt.write(crt.read())
            new_meta.write(meta.read())
