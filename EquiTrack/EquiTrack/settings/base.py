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
from sys import path
import datetime
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

import dj_database_url
import saml2
from saml2 import saml
from kombu import Exchange, Queue

# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)
SITE_NAME = basename(DJANGO_ROOT)

# DJANGO CORE SETTINGS ################################
# organized per https://docs.djangoproject.com/en/1.9/ref/settings/#core-settings-topical-index

# DJANGO: CACHE
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
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
DEBUG = os.environ.get('DJANGO_DEBUG', False)

if isinstance(DEBUG, str):
    if DEBUG.lower() == "true":
        DEBUG = True
    else:
        DEBUG = False

# DJANGO: EMAIL
DEFAULT_FROM_EMAIL = "no-reply@unicef.org"
EMAIL_BACKEND = 'post_office.EmailBackend'  # Will send email via our template system
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_PORT = os.environ.get('EMAIL_HOST_PORT', 587)
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', False)  # set True if using TLS

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
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'EquiTrack.mixins.EToolsTenantMiddleware',
    'EquiTrack.mixins.CSRFExemptMiddleware',
)
WSGI_APPLICATION = '%s.wsgi.application' % SITE_NAME

# DJANGO: LOGGING
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

# DJANGO: MODELS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'EquiTrack/data')),
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
    'suit',
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
    'suit_ckeditor',
    'generic_links',
    'gunicorn',
    'post_office',
    'djrill',
    'djcelery',
    'djcelery_email',
    'datetimewidget',
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

    'vision',
    'management',
    'publics',
    # you must list the app where your tenant model resides in
    'users',
    'notification',
)
TENANT_APPS = (
    'django_fsm',
    'logentry_admin',
    'reversion',
    'funds',
    'locations',
    'reports',
    'partners',
    'trips',
    'tpm',
    'supplies',
    't2f',
    'workplan',
    'actstream',
)
INSTALLED_APPS = SHARED_APPS + TENANT_APPS + ('tenant_schemas',)

# DJANGO: SECURITY
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
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
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

# DJANGO: TESTING
TEST_RUNNER = 'EquiTrack.tests.runners.TestRunner'

# DJANGO: URLS
ROOT_URLCONF = '%s.urls' % SITE_NAME

# Django Contrib Settings ################################

# CONTRIB: AUTH
AUTH_USER_MODEL = 'auth.User'
LOGIN_REDIRECT_URL = '/dash/'
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

# django-suit: http://django-suit.readthedocs.io/en/develop/configuration.html
SUIT_CONFIG = {
    'ADMIN_NAME': 'eTools',
    'SEARCH_URL': '/admin/partners/pca/',
    'CONFIRM_UNSAVED_CHANGES': False,
    'MENU': (
        {'app': 'auth', 'label': 'Users', 'icon': 'icon-user'},
        {'label': 'Dashboard', 'icon': 'icon-globe', 'url': 'dashboard'},
        {'app': 'funds', 'icon': 'icon-briefcase'},
        {'label': 'Result Structures', 'app': 'reports', 'icon': 'icon-info-sign', 'models': [
            {'model': 'reports.sector'},
            {'model': 'reports.result'},
            {'model': 'reports.indicator'},
            {'model': 'reports.goal'},
        ]},
        {'app': 'locations', 'icon': 'icon-map-marker'},
    )
}

# django-post_office: https://github.com/ui/django-post_office
POST_OFFICE = {
    'DEFAULT_PRIORITY': 'now',
    'BACKENDS': {
        # Will ensure email is sent async
        'default': 'djcelery_email.backends.CeleryEmailBackend'
    }
}

# django-celery: https://github.com/celery/django-celery
import djcelery
djcelery.setup_loader()

# celery: http://docs.celeryproject.org/en/3.1/configuration.html
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

# django-celery-email: https://github.com/pmclanahan/django-celery-email
CELERY_EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')

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
CORS_ORIGIN_ALLOW_ALL = True

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

# eTools settings ################################

COUCHBASE_URL = os.environ.get('COUCHBASE_URL')
COUCHBASE_USER = os.environ.get('COUCHBASE_USER')
COUCHBASE_PASS = os.environ.get('COUCHBASE_PASS')

DISABLE_INVOICING = True if os.getenv('DISABLE_INVOICING', False) in ['1', 'True', 'true'] else False

ENVIRONMENT = os.environ.get('ENVIRONMENT', '')
HOST = os.environ.get('DJANGO_ALLOWED_HOST', 'localhost:8000')

INACTIVE_BUSINESS_AREAS = os.environ.get('INACTIVE_BUSINESS_AREAS', '').split(',')

SLACK_URL = os.environ.get('SLACK_URL')

TASK_ADMIN_USER = os.environ.get('TASK_ADMIN_USER', 'etools_task_admin')

VISION_URL = os.getenv('VISION_URL', 'invalid_vision_url')
VISION_USER = os.getenv('VISION_USER', 'invalid_vision_user')
VISION_PASSWORD = os.getenv('VISION_PASSWORD', 'invalid_vision_password')

# Deprecated. I think all of these can be removed
BASE_DIR = dirname(SITE_ROOT)  # not used
AUTH_PROFILE_MODULE = 'users.UserProfile'  # no longer needed
MONGODB_URL = os.environ.get('MONGODB_URL', 'mongodb://localhost:27017')  # I don't see mongo being used
MONGODB_DATABASE = os.environ.get('MONGODB_DATABASE', 'supplies')
RAPIDPRO_TOKEN = os.environ.get('RAPIDPRO_TOKEN') # I don't see RapidPro installed
