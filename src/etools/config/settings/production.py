"""Production settings and globals."""
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate

from etools.config.settings.base import *  # noqa: F403

# Security settings for production
ALLOWED_HOSTS = [
    # Nope, regular expressions are not supported for this setting
    'etools.unicef.org',
    'etools-demo.unicef.org',
    'etools-dev.unicef.org',
    'etools-staging.unicef.org',
    'etools-test.unicef.org',
    'etools-test.unicef.io',
    '0.0.0.0'
]

ENV_HOST = get_from_secrets_or_env('DJANGO_ALLOWED_HOST', None)
if ENV_HOST:
    ALLOWED_HOSTS.append(ENV_HOST)


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
    STORAGES = {
        "default": {
            "BACKEND": 'etools.libraries.azure_storage_backend.EToolsAzureStorage'
        }
    }
    from storages.backends.azure_storage import AzureStorage
    storage = AzureStorage()
    with storage.open('keys/jwt/key.pem') as jwt_key, \
            storage.open('keys/jwt/certificate.pem') as jwt_cert, \
            storage.open('keys/vision/ezhact_cert.pem') as ezhact_cert, \
            storage.open('keys/vision/ezhact_key.pem') as ezhact_key:

        with open(os.path.join(CONFIG_ROOT, 'keys/jwt/key.pem'), 'wb+') as new_jwt_key, \
                open(os.path.join(CONFIG_ROOT, 'keys/jwt/certificate.pem'), 'wb+') as new_jwt_cert, \
                open(EZHACT_CERT_PATH, 'wb+') as new_ezhact_cert, \
                open(EZHACT_KEY_PATH, 'wb+') as new_ezhact_key:

            new_jwt_key.write(jwt_key.read())
            new_jwt_cert.write(jwt_cert.read())
            new_ezhact_cert.write(ezhact_cert.read())
            new_ezhact_key.write(ezhact_key.read())

# production overrides for django-rest-framework-jwt
if not get_from_secrets_or_env('DISABLE_JWT_LOGIN', False):
    private_key_bytes = open(join(CONFIG_ROOT, 'keys/jwt/key.pem'), 'rb').read()  # noqa: F405
    public_key_bytes = open(join(CONFIG_ROOT, 'keys/jwt/certificate.pem'), 'rb').read()  # noqa: F405

    JWT_PRIVATE_KEY = serialization.load_pem_private_key(private_key_bytes, password=None,
                                                         backend=default_backend())

    certificate = load_pem_x509_certificate(public_key_bytes, default_backend())
    JWT_PUBLIC_KEY = certificate.public_key()

    SIMPLE_JWT.update({  # noqa: F405
        'SIGNING_KEY': JWT_PRIVATE_KEY,
        'VERIFYING_KEY': JWT_PUBLIC_KEY,
        'AUDIENCE': 'https://etools.unicef.org/',
        'ALGORITHM': 'RS256',
    })
