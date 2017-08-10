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
SAML_ATTRIBUTE_MAPPING = {
    'upn': ('username',),
    'emailAddress': ('email',),
    'givenName': ('first_name',),
    'surname': ('last_name',),
}
SAML_DJANGO_USER_MAIN_ATTRIBUTE = 'email'
SAML_CREATE_UNKNOWN_USER = True
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
