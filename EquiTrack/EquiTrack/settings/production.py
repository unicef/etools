"""Production settings and globals."""

from os import environ
from base import *

########## HOST CONFIGURATION
# See: https://docs.djangoproject.com/en/1.5/releases/1.5/#allowed-hosts-required-in-production
ALLOWED_HOSTS = [
    os.environ.get('DJANGO_ALLOWED_HOST', '127.0.0.1'),
]
########## END HOST CONFIGURATION

# Sentry config
RAVEN_CONFIG = {
    'dsn': environ.get('SENTRY_DSN', None),
}

INSTALLED_APPS = INSTALLED_APPS + (
    'raven.contrib.django.raven_compat',
)

MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (
    'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
)

AZURE_ACCOUNT_NAME = os.environ.get('AZURE_ACCOUNT_NAME', None)
AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY', None)
AZURE_CONTAINER = os.environ.get('AZURE_CONTAINER', None)

if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY and AZURE_CONTAINER:

    DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
    MEDIA_URL = 'https://{}.blob.core.windows.net/{}/'.format(
        AZURE_ACCOUNT_NAME, AZURE_CONTAINER
    )
    FILER_IS_PUBLIC_DEFAULT = False
    FILER_STORAGES = {
        'public': {
            'main': {
                'ENGINE': 'storages.backends.s3boto.S3BotoStorage',
                'UPLOAD_TO': 'partners.utils.by_pca',
            },
        },
        'private': {
            'main': {
                'ENGINE': 'storages.backends.s3boto.S3BotoStorage',
                'UPLOAD_TO': 'partners.utils.by_pca',
            },
        },
    }


SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY)

LOGIN_URL = '/saml2/login/'
SAML_ATTRIBUTE_MAPPING = {
    'upn': ('username',),
    'emailAddress': ('email',),
    'givenname': ('first_name',),
    'surname': ('last_name',),
}
SAML_DJANGO_USER_MAIN_ATTRIBUTE = 'email'
SAML_CREATE_UNKNOWN_USER = True
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'djangosaml2.backends.Saml2Backend',
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
        "local": [join(DJANGO_ROOT, 'saml/FederationMetadata.xml')],
        # "remote": [
        #     {
        #         "url": "http://sts.unicef.org/federationmetadata/2007-06/federationmetadata.xml",
        #         "cert": join(DJANGO_ROOT, 'saml/certs/sts.unicef.org.cer')
        #     }
        # ],
    },

    # set to 1 to output debugging information
    'debug': 1,

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
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'
