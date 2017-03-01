"""Common settings and globals."""
from __future__ import absolute_import

import os
from os.path import abspath, basename, dirname, join, normpath
from sys import path
import datetime
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

import dj_database_url
import saml2
from saml2 import saml
from kombu import Exchange, Queue


########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# for Django 1.6
BASE_DIR = dirname(SITE_ROOT)

HOST = os.environ.get('DJANGO_ALLOWED_HOST', 'localhost:8000')
ENVIRONMENT = os.environ.get('ENVIRONMENT', '')

# Site name:
SITE_NAME = basename(DJANGO_ROOT)
SUIT_CONFIG = {
    'ADMIN_NAME': 'eTools',
    'SEARCH_URL': '/admin/partners/pca/',
    'CONFIRM_UNSAVED_CHANGES': False,

    'MENU': (

        {'app': 'auth', 'label': 'Users', 'icon': 'icon-user'},

        {'label': 'Dashboard', 'icon': 'icon-globe', 'url': 'dashboard'},

        {'label': 'Partnerships', 'icon': 'icon-pencil', 'models': [
            {'model': 'partners.partnerorganization', 'label': 'Partners'},
            {'model': 'partners.agreement'},
            {'model': 'partners.intervention'},
            {'model': 'partners.governmentintervention', 'label': 'Government'},
        ]},

        {'app': 'trips', 'icon': 'icon-road', 'models': [
            {'model': 'trips.trip'},
            {'model': 'trips.actionpoint'},
        ]},

        {'app': 'funds', 'icon': 'icon-briefcase'},

        {'label': 'Result Structures', 'app': 'reports', 'icon': 'icon-info-sign', 'models': [
            {'model': 'reports.resultstructure'},
            {'model': 'reports.sector'},
            {'model': 'reports.result'},
            {'model': 'reports.indicator'},
            {'model': 'reports.goal'},
        ]},

        #{'app': 'activityinfo', 'label': 'ActivityInfo'},

        {'app': 'locations', 'icon': 'icon-map-marker'},

        {'app': 'tpm', 'label': 'TPM Portal', 'icon': 'icon-calendar'},
    )
}

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dash/'
AUTH_USER_MODEL = 'auth.User'
AUTH_PROFILE_MODULE = 'users.UserProfile'

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
DEFAULT_FROM_EMAIL = "no-reply@unicef.org"
POST_OFFICE = {
    'DEFAULT_PRIORITY': 'now',
    'BACKENDS': {
        # Will ensure email is sent async
        'default': 'djcelery_email.backends.CeleryEmailBackend'
    }
}
EMAIL_BACKEND = 'post_office.EmailBackend'  # Will send email via our template system
CELERY_EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_PORT = os.environ.get('EMAIL_HOST_PORT', 587)
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', False) #set True if using TLS
########## END EMAIL CONFIGURATION

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

CORS_ORIGIN_ALLOW_ALL = True

SWAGGER_SETTINGS = {
    'is_authenticated': True,
    'is_superuser': True,
}

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)
########## END PATH CONFIGURATION

########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = os.environ.get('DJANGO_DEBUG', False)

if isinstance(DEBUG, str):
    if DEBUG.lower() == "true":
        DEBUG = True
    else:
        DEBUG = False

########## END DEBUG CONFIGURATION

########## DATABASE CONFIGURATION #########
POSTGIS_VERSION = (2, 1)
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

import djcelery
djcelery.setup_loader()
BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
BROKER_VISIBILITY_VAR = os.environ.get('CELERY_VISIBILITY_TIMEOUT', 1800)
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': int(BROKER_VISIBILITY_VAR)}  # 5 hours

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

# Don't use pickle as serializer, json is much safer
# CELERY_TASK_SERIALIZER = "json"
# CELERY_ACCEPT_CONTENT = ['application/json']

# CELERYD_HIJACK_ROOT_LOGGER = False
CELERYD_PREFETCH_MULTIPLIER = 1
# CELERYD_MAX_TASKS_PER_CHILD = 1000

SLACK_URL = os.environ.get('SLACK_URL')

COUCHBASE_URL = os.environ.get('COUCHBASE_URL')
COUCHBASE_USER = os.environ.get('COUCHBASE_USER')
COUCHBASE_PASS = os.environ.get('COUCHBASE_PASS')
INACTIVE_BUSINESS_AREAS = os.environ.get('INACTIVE_BUSINESS_AREAS', '').split(',')

MONGODB_URL = os.environ.get('MONGODB_URL', 'mongodb://localhost:27017')
MONGODB_DATABASE = os.environ.get('MONGODB_DATABASE', 'supplies')

# SESSION_ENGINE = 'redis_sessions_fork.session'
# SESSION_REDIS_URL = BROKER_URL
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
########## END DATABASE CONFIGURATION

VISION_URL = os.getenv('VISION_URL', 'invalid_vision_url')
VISION_USER = os.getenv('VISION_USER', 'invalid_vision_user')
VISION_PASSWORD = os.getenv('VISION_PASSWORD', 'invalid_vision_password')

USERVOICE_WIDGET_KEY = os.getenv('USERVOICE_KEY', '')
# ########## MANAGER CONFIGURATION
# # See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
# ADMINS = (
#     ('James Cranwell-Ward', 'jcranwellward@unicef.org'),
# )
#
# # See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
# MANAGERS = ADMINS
# ########## END MANAGER CONFIGURATION

########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'EET'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

DISABLE_INVOICING = True if os.getenv('DISABLE_INVOICING', False) in ['1', 'True', 'true'] else False
########## END GENERAL CONFIGURATION


########## ALLAUTH CONFIGURATION
SOCIALACCOUNT_PROVIDERS = \
    { 'google':
        { 'SCOPE': ['profile', 'email'],
          'AUTH_PARAMS': { 'access_type': 'online' } }}

SOCIALACCOUNT_ADAPTER = 'EquiTrack.mixins.CustomSocialAccountAdapter'
ACCOUNT_ADAPTER = 'EquiTrack.mixins.CustomAccountAdapter'

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_UNIQUE_EMAIL = True
# ACCOUNT_USERNAME_REQUIRED = False

SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_LOGOUT_REDIRECT_URL = "/login"
ACCOUNT_LOGOUT_ON_GET = True

ACCOUNT_EMAIL_VERIFICATION = "none"  # "optional", "mandatory" or "none"
########## END ALLAUTH CONFIGURATION

########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(SITE_ROOT, 'media'))

MEDIA_URL = '/media/'
STATIC_URL = '/static/'

########## END MEDIA CONFIGURATION

########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(SITE_ROOT, 'static'))

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'assets')),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
########## END STATIC FILE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key should only be used for development and testing.
SECRET_KEY = r"j8%#f%3t@9)el9jh4f0ug4*mm346+wwwti#6(^@_ksf@&k^ob1"
########## END SECRET CONFIGURATION

RAPIDPRO_TOKEN = os.environ.get('RAPIDPRO_TOKEN')

########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'EquiTrack/data')),
)
########## END FIXTURE CONFIGURATION


########## TEMPLATE CONFIGURATION
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            normpath(join(SITE_ROOT, 'templates')),
            normpath(join(SITE_ROOT, 'templates', 'frontend'))
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,  # TEMPLATE_DEBUG was deprecated
            'context_processors': [
                # Already defined Django-related contexts here

                # `allauth` needs this from django
                'django.contrib.auth.context_processors.auth',
                'django.core.context_processors.request',
                'django.core.context_processors.debug',
                'django.core.context_processors.i18n',
                'django.core.context_processors.media',
                'django.core.context_processors.static',
                'django.core.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    # Default Django middleware.
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'EquiTrack.mixins.EToolsTenantMiddleware',
    'EquiTrack.mixins.CSRFExemptMiddleware',
)
########## END MIDDLEWARE CONFIGURATION


########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION


########## APP CONFIGURATION
SHARED_APPS = (
    # Default Django apps:
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
    # Useful template tags:
    # 'django.contrib.humanize',
    'suit',
    'django.contrib.admin',
    # 'django.contrib.admindocs',
    'django.contrib.humanize',
    'mathfilters',

    'easy_thumbnails',
    'storages',
    'rest_framework',
    'rest_framework_swagger',
    'rest_framework.authtoken',
    'import_export',
    'smart_selects',
    'suit_ckeditor',
    'generic_links',
    'gunicorn',
    'post_office',
    'djrill',
    'djcelery',
    'djcelery_email',
    'datetimewidget',
    'leaflet',
    'djgeojson',
    'paintstore',
    'corsheaders',
    'djangosaml2',
    #allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # allauth providers you want to enable:
    #'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.google',
    #'allauth.socialaccount.providers.twitter',
    'analytical',
    'mptt',
    'easy_pdf',
    'django_hstore',

    'vision',
    'management',
    'publics',
    # you must list the app where your tenant model resides in
    'users',
    'notification',
)

MPTT_ADMIN_LEVEL_INDENT = 20

# Apps specific for this project go here.
TENANT_APPS = (
    'django_fsm',
    'logentry_admin',
    'reversion',
    'funds',
    'locations',
    'activityinfo',
    'reports',
    'partners',
    'trips',
    'tpm',
    'supplies',
    't2f',
    'workplan',
    'actstream',
)


LEAFLET_CONFIG = {
    'TILES':  'http://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    'ATTRIBUTION_PREFIX': 'Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012',
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
}

ACTSTREAM_SETTINGS = {
    'FETCH_RELATIONS': True,
    'GFK_FETCH_DEPTH': 1,
    'USE_JSONFIELD': True,
    'MANAGER': 'EquiTrack.stream_feed.managers.CustomDataActionManager',
}

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = SHARED_APPS + TENANT_APPS + ('tenant_schemas',)
TENANT_MODEL = "users.Country"  # app.Model
########## END APP CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION


########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = '%s.wsgi.application' % SITE_NAME
########## END WSGI CONFIGURATION

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
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
