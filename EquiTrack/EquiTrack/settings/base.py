"""
Django settings for UNICEF eTools project.

* Common or default settings are included in this file (base.py).
* Production settings are in production.py.
* Local developer and testing settings are in local.py.
* Custom developer settings are optionally in custom.py (See custom.example.py for docs)

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""
from __future__ import absolute_import

import os
from os.path import abspath, basename, dirname, join, normpath
import datetime

import djcelery
import dj_database_url
import saml2
from saml2 import saml


# Helper function to convert strings (i.e. environment variable values) to a Boolean
def str2bool(value):
    """
    Given a string 'value', return a Boolean which that string represents.

    This assumes that 'value' is one of a list of some common possible Truthy string values.
    """
    return str(value).lower() in ("yes", "true", "t", "1")


# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)
SITE_NAME = basename(DJANGO_ROOT)

# DJANGO CORE SETTINGS ################################
# organized per https://docs.djangoproject.com/en/1.9/ref/settings/#core-settings-topical-index

# DJANGO: CACHE
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    }
}

# DJANGO: DATABASE
db_config = dj_database_url.config(
    env="DATABASE_URL",
    default='postgis:///etools'
)
ORIGINAL_BACKEND = 'django.contrib.gis.db.backends.postgis'
db_config['ENGINE'] = 'tenant_schemas.postgresql_backend'
db_config['CONN_MAX_AGE'] = 0
DATABASES = {
    'default': db_config
}
DATABASE_ROUTERS = (
    'tenant_schemas.routers.TenantSyncRouter',
)

# DJANGO: DEBUGGING
DEBUG = str2bool(os.environ.get('DJANGO_DEBUG'))

# DJANGO: EMAIL
DEFAULT_FROM_EMAIL = "no-reply@unicef.org"
EMAIL_BACKEND = 'post_office.EmailBackend'  # Will send email via our template system
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_PORT = os.environ.get('EMAIL_HOST_PORT', 587)
EMAIL_USE_TLS = str2bool(os.environ.get('EMAIL_USE_TLS'))  # set True if using TLS

# DJANGO: ERROR REPORTING

# DJANGO: FILE UPLOADS
MEDIA_ROOT = normpath(join(SITE_ROOT, 'media'))
MEDIA_URL = '/media/'

# DJANGO: GLOBALIZATION (I18N/L10N)
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# DJANGO: HTTP
MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'EquiTrack.mixins.EToolsTenantMiddleware',
)
WSGI_APPLICATION = '%s.wsgi.application' % SITE_NAME

# DJANGO: LOGGING
LOGGING = {
    'version': 1,
    'disable_existing_loggers': str2bool(os.environ.get('DJANGO_DISABLE_EXISTING_LOGGERS', 'True')),
    'handlers': {
        # Send all messages to console
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO'
        },
    },
    'django.security.DisallowedHost': {
        'handlers': ['null'],
        'propagate': False,
    },
    'root': {
        'handlers': ['console', ],
        'level': 'INFO'
    },
}

# DJANGO: MODELS
FIXTURE_DIRS = (
    normpath(join(DJANGO_ROOT, 'data')),
)
SHARED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dal',
    'dal_select2',
    'django.contrib.gis',
    'django.contrib.postgres',
    'django.contrib.admin',
    'django.contrib.humanize',
    'mathfilters',

    'easy_thumbnails',
    'storages',
    'rest_framework',
    'rest_framework_swagger',
    'rest_framework.authtoken',
    'import_export',
    'smart_selects',
    'generic_links',
    'gunicorn',
    'post_office',
    'djrill',
    'djcelery',
    'djcelery_email',
    'leaflet',
    'paintstore',
    'corsheaders',
    'djangosaml2',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # allauth providers you want to enable:
    # 'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.google',
    # 'allauth.socialaccount.providers.twitter',
    'analytical',
    'mptt',
    'easy_pdf',
    'ordered_model',
    'vision',
    'publics',
    # you must list the app where your tenant model resides in
    'users',
    'notification',
    'django_filters',
    'environment',
    'utils.common',
    'utils.mail',
    'utils.writable_serializers',
    'utils.permissions',
)
TENANT_APPS = (
    'django_fsm',
    'logentry_admin',
    'funds',
    'locations',
    'reports',
    'partners',
    'trips',
    'supplies',
    'activities',
    't2f',
    'workplan',
    'actstream',
    'attachments',
    'tpm',
    'audit',
    'firms',
    'management',
)
INSTALLED_APPS = ('tenant_schemas',) + SHARED_APPS + TENANT_APPS

# DJANGO: SECURITY
ALLOWED_HOSTS = [
    os.environ.get('DJANGO_ALLOWED_HOST', '127.0.0.1'),
]
SECRET_KEY = r"j8%#f%3t@9)el9jh4f0ug4*mm346+wwwti#6(^@_ksf@&k^ob1"  # only used locally

# DJANGO: SERIALIZATION

# DJANGO: TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            normpath(join(SITE_ROOT, 'templates')),
            normpath(join(SITE_ROOT, 'templates', 'frontend'))
        ],
        'APP_DIRS': False,  # False because we set loaders manually below
        'OPTIONS': {
            'debug': DEBUG,
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'utils.mail.loaders.EmailTemplateLoader',
            ],
            'context_processors': [
                # Already defined Django-related contexts here

                # `allauth` needs this from django
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# DJANGO: TESTING
TEST_RUNNER = 'EquiTrack.tests.runners.TestRunner'

# DJANGO: URLS
ROOT_URLCONF = '%s.urls' % SITE_NAME


# Django Contrib Settings ################################

# CONTRIB: AUTH
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'djangosaml2.backends.Saml2Backend',
    'allauth.account.auth_backends.AuthenticationBackend',
)
AUTH_USER_MODEL = 'auth.User'
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/login/'

# CONTRIB: GIS (GeoDjango)
POSTGIS_VERSION = (2, 1)

# CONTRIB: MESSAGES

# CONTRIB: SESSIONS
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# CONTRIB: SITES
SITE_ID = 1

# CONTRIB: STATIC FILES
STATIC_ROOT = normpath(join(SITE_ROOT, 'static'))
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'assets')),
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)


# Third party library settings ################################

# django-post_office: https://github.com/ui/django-post_office
POST_OFFICE = {
    'DEFAULT_PRIORITY': 'now',
    'BACKENDS': {
        # Will ensure email is sent async
        'default': 'djcelery_email.backends.CeleryEmailBackend'
    }
}

# django-celery: https://github.com/celery/django-celery
djcelery.setup_loader()

# celery: http://docs.celeryproject.org/en/3.1/configuration.html
BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
BROKER_VISIBILITY_VAR = os.environ.get('CELERY_VISIBILITY_TIMEOUT', 1800)  # in seconds
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': int(BROKER_VISIBILITY_VAR)}
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
# Sensible settings for celery
CELERY_ALWAYS_EAGER = False
CELERY_ACKS_LATE = True
CELERY_TASK_PUBLISH_RETRY = True
CELERY_DISABLE_RATE_LIMITS = False
# By default we will ignore result
# If you want to see results and try out tasks interactively, change it to False
# Or change this setting on tasks level
CELERY_IGNORE_RESULT = True
CELERY_SEND_TASK_ERROR_EMAILS = False
CELERY_TASK_RESULT_EXPIRES = 600
CELERYD_PREFETCH_MULTIPLIER = 1

# django-celery-email: https://github.com/pmclanahan/django-celery-email
CELERY_EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
CELERY_ROUTES = {
    'vision.tasks.sync_handler': {'queue': 'vision_queue'}
}

# djangorestframework: http://www.django-rest-framework.org/api-guide/settings/
REST_FRAMEWORK = {
    # this setting fixes the bug where user can be logged in as AnonymousUser
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework_csv.renderers.CSVRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'EquiTrack.mixins.EToolsTenantJWTAuthentication',
        'EquiTrack.mixins.EtoolsTokenAuthentication',
    ),
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework_csv.renderers.CSVRenderer',
        'rest_framework_xml.renderers.XMLRenderer',
    )
}

# django-cors-headers: https://github.com/ottoyiu/django-cors-headers
CORS_ORIGIN_ALLOW_ALL = False

# django-rest-swagger: http://django-rest-swagger.readthedocs.io/en/latest/settings/
SWAGGER_SETTINGS = {
    'is_authenticated': True,
    'is_superuser': True,
}

# django-analytical: https://pythonhosted.org/django-analytical/
USERVOICE_WIDGET_KEY = os.getenv('USERVOICE_KEY', '')

# django-allauth: https://github.com/pennersr/django-allauth
ACCOUNT_ADAPTER = 'EquiTrack.mixins.CustomAccountAdapter'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "none"  # "optional", "mandatory" or "none"
ACCOUNT_LOGOUT_REDIRECT_URL = "/login"
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = 'EquiTrack.mixins.CustomSocialAccountAdapter'
SOCIALACCOUNT_PROVIDERS = \
    {'google':
        {'SCOPE': ['profile', 'email'],
         'AUTH_PARAMS': {'access_type': 'online'}}}
SOCIALACCOUNT_STORE_TOKENS = True

# django-mptt: https://github.com/django-mptt/django-mptt
MPTT_ADMIN_LEVEL_INDENT = 20

# django-leaflet: django-leaflet
LEAFLET_CONFIG = {
    'TILES':  'http://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    'ATTRIBUTION_PREFIX': 'Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012',  # noqa
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
}

# django-activity-stream: http://django-activity-stream.readthedocs.io/en/latest/configuration.html
ACTSTREAM_SETTINGS = {
    'FETCH_RELATIONS': True,
    'GFK_FETCH_DEPTH': 1,
    'USE_JSONFIELD': True,
    'MANAGER': 'EquiTrack.stream_feed.managers.CustomDataActionManager',
}

# django-tenant-schemas: https://github.com/bernardopires/django-tenant-schemas
TENANT_MODEL = "users.Country"  # app.Model

# django-saml2: https://github.com/robertavram/djangosaml2
HOST = os.environ.get('DJANGO_ALLOWED_HOST', 'localhost:8000')
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

# django-rest-framework-jwt: http://getblimp.github.io/django-rest-framework-jwt/
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

   'JWT_ALGORITHM': 'HS256',
   'JWT_VERIFY': True,
   'JWT_VERIFY_EXPIRATION': True,
   'JWT_LEEWAY': 30,
   'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=30000),
   'JWT_AUDIENCE': None,
   'JWT_ISSUER': None,

   'JWT_ALLOW_REFRESH': False,
   'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),

   'JWT_AUTH_HEADER_PREFIX': 'JWT',
}


# eTools settings ################################

COUCHBASE_URL = os.environ.get('COUCHBASE_URL')
COUCHBASE_USER = os.environ.get('COUCHBASE_USER')
COUCHBASE_PASS = os.environ.get('COUCHBASE_PASS')

DISABLE_INVOICING = str2bool(os.getenv('DISABLE_INVOICING'))

ENVIRONMENT = os.environ.get('ENVIRONMENT', '')
ETRIPS_VERSION = os.environ.get('ETRIPS_VERSION')

INACTIVE_BUSINESS_AREAS = os.environ.get('INACTIVE_BUSINESS_AREAS', '').split(',')

SLACK_URL = os.environ.get('SLACK_URL')

TASK_ADMIN_USER = os.environ.get('TASK_ADMIN_USER', 'etools_task_admin')

VISION_URL = os.getenv('VISION_URL', 'invalid_vision_url')
VISION_USER = os.getenv('VISION_USER', 'invalid_vision_user')
VISION_PASSWORD = os.getenv('VISION_PASSWORD', 'invalid_vision_password')

ISSUE_CHECKS = [
    'management.issues.project_checks.ActivePCANoSignedDocCheck',
    'management.issues.project_checks.PdOutputsWrongCheck',
    'management.issues.project_checks.InterventionsAssociatedSSFACheck',
    'management.issues.project_checks.InterventionsAreValidCheck',
    'management.issues.project_checks.PDAmendmentsMissingFilesCheck',
    'management.issues.project_checks.PCAAmendmentsMissingFilesCheck',
]

EMAIL_FOR_USER_RESPONSIBLE_FOR_INVESTIGATION_ESCALATIONS = os.getenv(
    'EMAIL_FOR_USER_RESPONSIBLE_FOR_INVESTIGATION_ESCALATIONS', 'integrity1@un.org'
)
