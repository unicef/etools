"""Production settings and globals."""

from os import environ
from base import *

ALLOWED_HOSTS = [
    os.environ.get('DJANGO_ALLOWED_HOST', '127.0.0.1'),
]

# raven (Sentry): https://github.com/getsentry/raven-python
RAVEN_CONFIG = {
    'dsn': environ.get('SENTRY_DSN', None),
}
INSTALLED_APPS += (  # noqa
    'raven.contrib.django.raven_compat',
)

# django-allauth: https://github.com/pennersr/django-allauth
SOCIALACCOUNT_PROVIDERS = \
    {'google':
        {'SCOPE': ['profile', 'email'],
         'AUTH_PARAMS': {'access_type': 'online'}}}
SOCIALACCOUNT_ADAPTER = 'EquiTrack.mixins.CustomSocialAccountAdapter'
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

# django-cors-headers: https://github.com/ottoyiu/django-cors-headers
CORS_ORIGIN_ALLOW_ALL = False

# eTools settings
ETRIPS_VERSION = environ.get('ETRIPS_VERSION', None)

# Azure settings
AZURE_ACCOUNT_NAME = os.environ.get('AZURE_ACCOUNT_NAME', None)
AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY', None)
AZURE_CONTAINER = os.environ.get('AZURE_CONTAINER', None)
AZURE_SSL = True
AZURE_AUTO_SIGN = True  # flag for automatically signing urls
AZURE_ACCESS_POLICY_EXPIRY = 120  # length of time before signature expires in seconds
AZURE_ACCESS_POLICY_PERMISSION = 'r'  # read permission

if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY and AZURE_CONTAINER:

    DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
    # MEDIA_URL = 'https://{}.blob.core.windows.net/{}/'.format(
    #     AZURE_ACCOUNT_NAME, AZURE_CONTAINER
    # )

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


SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'


LOGIN_URL = '/login/'
SAML_ATTRIBUTE_MAPPING = {
    'upn': ('username',),
    'emailAddress': ('email',),
    'givenName': ('first_name',),
    'surname': ('last_name',),
}
SAML_DJANGO_USER_MAIN_ATTRIBUTE = 'email'
SAML_CREATE_UNKNOWN_USER = True
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'djangosaml2.backends.Saml2Backend',
    'allauth.account.auth_backends.AuthenticationBackend',
)
SAML_CONFIG = {
    # full path to the xmlsec1 binary programm
    'xmlsec_binary': '/usr/bin/xmlsec1',

    # your entity id, usually your subdomain plus the url to the metadata view
    'entityid': 'https://{}/saml2/metadata/'.format(HOST),

    # directory with attribute mapping
    'attribute_map_dir': join(DJANGO_ROOT, 'saml/attribute-maps'),

    # this block states what services we provide
    'service': {
        # we are just a lonely SP
        'sp': {
            'name': 'eTools',
            'name_id_format': saml.NAMEID_FORMAT_PERSISTENT,
            'endpoints': {
                # url and binding to the assetion consumer service view
                # do not change the binding or service name
                'assertion_consumer_service': [
                    ('https://{}/saml2/acs/'.format(HOST),
                     saml2.BINDING_HTTP_POST),
                ],
                # url and binding to the single logout service view
                # do not change the binding or service name
                'single_logout_service': [
                    ('https://{}/saml2/ls/'.format(HOST),
                     saml2.BINDING_HTTP_REDIRECT),
                    ('https://{}/saml2/ls/post'.format(HOST),
                     saml2.BINDING_HTTP_POST),
                ],

            },

            # attributes that this project needs to identify a user
            'required_attributes': ['upn', 'emailAddress'],
        },
    },
    # where the remote metadata is stored
    'metadata': {
        "local": [join(DJANGO_ROOT, 'saml/federationmetadata.xml')],
        # "remote": [
        #     {
        #         "url": "http://sts.unicef.org/federationmetadata/2007-06/federationmetadata.xml",
        #         "cert": join(DJANGO_ROOT, 'saml/certs/sts.unicef.org.cer')
        #     }
        # ],
    },

    # set to 1 to output debugging information
    'debug': 1,

    # allow 300 seconds for time difference between adfs server and etools server
    'accepted_time_diff': 300,  # in seconds

    # certificate
    'key_file': join(DJANGO_ROOT, 'saml/certs/saml.key'),  # private part
    'cert_file': join(DJANGO_ROOT, 'saml/certs/sp.crt'),  # public part

    # own metadata settings
    'contact_person': [
        {'given_name': 'James',
         'sur_name': 'Cranwell-Ward',
         'company': 'UNICEF',
         'email_address': 'jcranwellward@unicef.org',
         'contact_type': 'technical'},
    ],
    # you can set multilanguage information here
    'organization': {
        'name': [('UNICEF', 'en')],
        'display_name': [('UNICEF', 'en')],
        'url': [('http://www.unicef.org', 'en')],
    },
    'valid_for': 24,  # how long is our metadata valid
}
SAML_SIGNED_LOGOUT = True

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

########## CACHE CONFIGURATION
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': environ.get('REDIS_URL', 'redis://localhost:6379/0')
    }
}
########## END CACHE CONFIGURATION
