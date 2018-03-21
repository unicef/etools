import logging
import sys

from EquiTrack.settings.base import *  # noqa: F403

ALLOWED_HOSTS = ['*']
DEBUG = True
CELERY_TASK_ALWAYS_EAGER = True

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
elif 'runserver' in sys.argv:
    # Settings which should only be active when running a local server

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

SHELL_PLUS_PRE_IMPORTS = (
    ('EquiTrack.util_scripts', '*'),
)

# django-storages: https://django-storages.readthedocs.io/en/latest/backends/azure.html
AZURE_ACCOUNT_NAME = os.environ.get('AZURE_ACCOUNT_NAME')  # noqa: F405
AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY')  # noqa: F405
AZURE_CONTAINER = os.environ.get('AZURE_CONTAINER')  # noqa: F405
AZURE_SSL = True
AZURE_AUTO_SIGN = True  # flag for automatically signing urls
AZURE_ACCESS_POLICY_EXPIRY = 10800  # length of time before signature expires in seconds
AZURE_ACCESS_POLICY_PERMISSION = 'r'  # read permission

if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY and AZURE_CONTAINER:
    DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
    # from storages.backends.azure_storage import AzureStorage
    # storage = AzureStorage()
    # with storage.open('saml/certs/saml.key') as key, \
    #         storage.open('saml/certs/sp.crt') as crt, \
    #         storage.open('saml/federationmetadata.xml') as meta, \
    #         storage.open('keys/jwt/key.pem') as jwt_key, \
    #         storage.open('keys/jwt/certificate.pem') as jwt_cert:
    #
    #     with open('EquiTrack/saml/certs/saml.key', 'w+') as new_key, \
    #             open('EquiTrack/saml/certs/sp.crt', 'w+') as new_crt, \
    #             open('EquiTrack/keys/jwt/key.pem', 'w+') as new_jwt_key, \
    #             open('EquiTrack/keys/jwt/certificate.pem', 'w+') as new_jwt_cert, \
    #             open('EquiTrack/saml/federationmetadata.xml', 'w+') as new_meta:
    #
    #         new_key.write(key.read())
    #         new_crt.write(crt.read())
    #         new_meta.write(meta.read())
    #         new_jwt_key.write(jwt_key.read())
    #         new_jwt_cert.write(jwt_cert.read())
