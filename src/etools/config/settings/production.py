"""Production settings and globals."""
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate

from etools.config.settings.base import *  # noqa: F403

# raven (Sentry): https://github.com/getsentry/raven-python
RAVEN_CONFIG = {
    'dsn': get_from_secrets_or_env('SENTRY_DSN'),  # noqa: F405
}
# Override default client, in order to send extra data to Sentry
SENTRY_CLIENT = 'etools.config.sentry.EToolsSentryClient'
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
    '0.0.0.0'
]
SECRET_KEY = os.environ["SECRET_KEY"]  # noqa: F405
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# django-storages: https://django-storages.readthedocs.io/en/latest/backends/azure.html
AZURE_ACCOUNT_NAME = get_from_secrets_or_env('AZURE_ACCOUNT_NAME')  # noqa: F405
AZURE_ACCOUNT_KEY = get_from_secrets_or_env('AZURE_ACCOUNT_KEY')  # noqa: F405
AZURE_CONTAINER = get_from_secrets_or_env('AZURE_CONTAINER')  # noqa: F405
AZURE_SSL = True
AZURE_AUTO_SIGN = True  # flag for automatically signing urls
AZURE_ACCESS_POLICY_EXPIRY = 10800  # length of time before signature expires in seconds
AZURE_ACCESS_POLICY_PERMISSION = 'r'  # read permission

if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY and AZURE_CONTAINER:
    DEFAULT_FILE_STORAGE = 'etools.libraries.azure_storage_backend.EToolsAzureStorage'
    from storages.backends.azure_storage import AzureStorage
    storage = AzureStorage()
    with storage.open('saml/certs/saml.key') as key, \
            storage.open('saml/certs/sp.crt') as crt, \
            storage.open('saml/federationmetadata.xml') as meta, \
            storage.open('keys/jwt/key.pem') as jwt_key, \
            storage.open('keys/jwt/certificate.pem') as jwt_cert:

        with open(os.path.join(CONFIG_ROOT, 'saml/certs/saml.key'), 'wb+') as new_key, \
                open(os.path.join(CONFIG_ROOT, 'saml/certs/sp.crt'), 'wb+') as new_crt, \
                open(os.path.join(CONFIG_ROOT, 'keys/jwt/key.pem'), 'wb+') as new_jwt_key, \
                open(os.path.join(CONFIG_ROOT, 'keys/jwt/certificate.pem'), 'wb+') as new_jwt_cert, \
                open(os.path.join(CONFIG_ROOT, 'saml/federationmetadata.xml'), 'wb+') as new_meta:

            new_key.write(key.read())
            new_crt.write(crt.read())
            new_meta.write(meta.read())
            new_jwt_key.write(jwt_key.read())
            new_jwt_cert.write(jwt_cert.read())

# production overrides for django-rest-framework-jwt
if not get_from_secrets_or_env('DISABLE_JWT_LOGIN', False):
    private_key_bytes = open(join(CONFIG_ROOT, 'keys/jwt/key.pem'), 'rb').read()  # noqa: F405
    public_key_bytes = open(join(CONFIG_ROOT, 'keys/jwt/certificate.pem'), 'rb').read()  # noqa: F405

    JWT_PRIVATE_KEY = serialization.load_pem_private_key(private_key_bytes, password=None,
                                                         backend=default_backend())

    certificate = load_pem_x509_certificate(public_key_bytes, default_backend())
    JWT_PUBLIC_KEY = certificate.public_key()

    JWT_AUTH.update({  # noqa: F405
        'JWT_SECRET_KEY': SECRET_KEY,
        'JWT_PUBLIC_KEY': JWT_PUBLIC_KEY,
        'JWT_PRIVATE_KEY': JWT_PRIVATE_KEY,
        'JWT_ALGORITHM': 'RS256',
        'JWT_LEEWAY': 60,
        'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=3000),  # noqa: F405
        'JWT_AUDIENCE': 'https://etools.unicef.org/',
        'JWT_PAYLOAD_HANDLER': 'etools.applications.EquiTrack.auth.custom_jwt_payload_handler'
    })
