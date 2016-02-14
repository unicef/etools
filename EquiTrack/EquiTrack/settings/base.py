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
            {'model': 'partners.pca'},
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

        #{'app': 'filer', 'label': 'Files', 'icon': 'icon-file'},

        #{'app': 'tpm', 'label': 'TPM Portal', 'icon': 'icon-calendar'},
    )
}

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
AUTH_USER_MODEL = 'auth.User'
AUTH_PROFILE_MODULE = 'users.UserProfile'

REGISTRATION_OPEN = True
ACCOUNT_ACTIVATION_DAYS = 7

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
CELERY_EMAIL_BACKEND = "djrill.mail.backends.djrill.DjrillBackend"  # Will send mail via mandrill service
MANDRILL_API_KEY = os.environ.get("MANDRILL_KEY", 'notarealkey')
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
    )
}

CORS_ORIGIN_ALLOW_ALL = True

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

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION

########## DATABASE CONFIGURATION #########
POSTGIS_VERSION = (2, 1)
db_config = dj_database_url.config(
    env="DATABASE_URL",
    default='postgis:///etools'
)
ORIGINAL_BACKEND = 'django.contrib.gis.db.backends.postgis'
db_config['ENGINE'] = 'tenant_schemas.postgresql_backend'
DATABASES = {
    'default': db_config
}
DATABASE_ROUTERS = (
    'tenant_schemas.routers.TenantSyncRouter',
)

import djcelery
djcelery.setup_loader()
BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

SLACK_URL = os.environ.get('SLACK_URL')

COUCHBASE_URL = os.environ.get('COUCHBASE_URL')
COUCHBASE_USER = os.environ.get('COUCHBASE_USER')
COUCHBASE_PASS = os.environ.get('COUCHBASE_PASS')

MONGODB_URL = os.environ.get('MONGODB_URL', 'mongodb://localhost:27017')
MONGODB_DATABASE = os.environ.get('MONGODB_DATABASE', 'supplies')
########## END DATABASE CONFIGURATION

VISION_USER = os.getenv('VISION_USER', 'invalid_vision_user')
VISION_PASSWORD = os.getenv('VISION_PASSWORD', 'invalid_vision_password')
VISION_URL = 'https://devapis.unicef.org/BIService/BIWebService.svc/'

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

########## SITE CONFIGURATION
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []
########## END SITE CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION


########## TEMPLATE CONFIGURATION
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [normpath(join(SITE_ROOT, 'templates')), normpath(join(SITE_ROOT, 'templates', 'frontend'))],
        'APP_DIRS': True,
        'OPTIONS': {
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
    'django.contrib.gis',
    'django.contrib.postgres',
    # Useful template tags:
    # 'django.contrib.humanize',

    # Admin panel and documentation:
    'autocomplete_light',
    'suit',
    'django.contrib.admin',
    # 'django.contrib.admindocs',
    'django.contrib.humanize',
    'mathfilters',

    'easy_thumbnails',
    'filer',
    'storages',
    'reversion',
    'rest_framework',
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
    'logentry_admin',
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
    'vision',

    # you must list the app where your tenant model resides in
    'users',
    'management',
)

MPTT_ADMIN_LEVEL_INDENT = 20

# Apps specific for this project go here.
TENANT_APPS = (
    'funds',
    'locations',
    'activityinfo',
    'reports',
    'partners',
    'trips',
    'tpm',
    'supplies',
)


LEAFLET_CONFIG = {
    'TILES':  'http://otile1.mqcdn.com/tiles/1.0.0/map/{z}/{x}/{y}.jpg',
    'ATTRIBUTION_PREFIX': 'Tiles Courtesy of <a href="http://www.mapquest.com/" target="_blank">MapQuest</a> <img src="http://developer.mapquest.com/content/osm/mq_logo.png">',
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
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