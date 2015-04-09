"""Common settings and globals."""
from __future__ import absolute_import

import os
from os.path import abspath, basename, dirname, join, normpath
from sys import path


########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# for Django 1.6
BASE_DIR = dirname(SITE_ROOT)

# Site name:
SITE_NAME = basename(DJANGO_ROOT)
SUIT_CONFIG = {
    'ADMIN_NAME': 'EquiTrack',
    'SEARCH_URL': '/admin/partners/pca/',
    'CONFIRM_UNSAVED_CHANGES': False,

    'MENU': (

        {'app': 'auth', 'label': 'Users', 'icon': 'icon-user'},

        {'label': 'Dashboard', 'icon': 'icon-dashboard', 'url': 'dashboard'},

        {'label': 'Partnerships', 'icon': 'icon-pencil', 'models': [
            {'model': 'partners.pca', 'label': 'Partnerships'},
            {'model': 'partners.assessment', 'label': 'Assessments'},
            {'model': 'partners.partnerorganization', 'label': 'Partners'},
            {'model': 'partners.face', 'label': 'FACE'},
        ]},

        {'app': 'trips', 'icon': 'icon-road', 'models': [
            {'model': 'trips.trip'},
            {'model': 'trips.actionpoint'},
            {'model': 'trips.office'},
        ]},

        {'app': 'funds', 'icon': 'icon-briefcase'},

        {'label': 'Result Structures', 'app': 'reports', 'icon': 'icon-info-sign', 'models': [
            {'model': 'reports.resultstructure'},
            {'model': 'reports.sector'},
            {'model': 'reports.result'},
            {'model': 'reports.indicator'},
            {'model': 'reports.goal'},
            {'model': 'reports.intermediateresult'},
            {'model': 'reports.wbs'},
        ]},

        {'app': 'activityinfo', 'label': 'ActivityInfo'},

        {'app': 'locations', 'icon': 'icon-globe'},

        {'app': 'filer', 'label': 'Files', 'icon': 'icon-file'},

        {'app': 'tpm', 'label': 'TPM Portal', 'icon': 'icon-calendar'},
    )
}

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
AUTH_USER_MODEL = 'auth.User'
AUTH_PROFILE_MODULE = 'users.UserProfile'

REGISTRATION_OPEN = True
ACCOUNT_ACTIVATION_DAYS = 7
DEFAULT_FROM_EMAIL = "no-reply@unicef.org"
POST_OFFICE = {
    'DEFAULT_PRIORITY': 'now'
}


REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework_csv.renderers.CSVRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
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
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        env="DATABASE_URL",
        default='postgis:///equitrack'
    )
}
BROKER_URL = 'redis://localhost:6379/0'
CELERY_ALWAYS_EAGER = os.environ.get('CELERY_EAGER', True)
CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
CELERY_BEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
########## END DATABASE CONFIGURATION

########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('James Cranwell-Ward', 'jcranwellward@unicef.org'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


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


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(BASE_DIR, 'media'))

FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS = True
FILER_STORAGES = {
    'public': {
        'main': {
            'ENGINE': 'filer.storage.PublicFileSystemStorage',
            'OPTIONS': {
                'location': MEDIA_ROOT,
                'base_url': '/media/filer/',
            },
            'UPLOAD_TO': 'partners.utils.by_pca'
        },
    },
    'private': {
        'main': {
            'ENGINE': 'filer.storage.PrivateFileSystemStorage',
            'OPTIONS': {
                'location': MEDIA_ROOT,
                'base_url': '/media/filer/',
            },
            'UPLOAD_TO': 'partners.utils.by_pca'
        },
    },
}

MEDIA_URL = '/media/'
STATIC_URL = '/static/'

########## END MEDIA CONFIGURATION

########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(BASE_DIR, 'static'))

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'assets')),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# The baseUrl to pass to the r.js optimizer.
REQUIRE_BASE_URL = normpath(join(STATIC_ROOT, 'js'))

# The name of a build profile to use for your project, relative to REQUIRE_BASE_URL.
# A sensible value would be 'app.build.js'. Leave blank to use the built-in default build profile.
# Set to False to disable running the default profile (e.g. if only using it to build Standalone
# Modules)
REQUIRE_BUILD_PROFILE = None

# The name of the require.js script used by your project, relative to REQUIRE_BASE_URL.
REQUIRE_JS = "main.js"

# A dictionary of standalone modules to build with almond.js.
# See the section on Standalone Modules, below.
REQUIRE_STANDALONE_MODULES = {}

# Whether to run django-require in debug mode.
REQUIRE_DEBUG = DEBUG

# A tuple of files to exclude from the compilation result of r.js.
REQUIRE_EXCLUDE = ("build.txt",)

# The execution environment in which to run r.js: auto, node or rhino.
# auto will autodetect the environment and make use of node if available and rhino if not.
# It can also be a path to a custom class that subclasses require.environments.Environment
# and defines some "args" function that returns a list with the command arguments to execute.
REQUIRE_ENVIRONMENT = "auto"
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
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
TEMPLATE_DIRS = (
    normpath(join(SITE_ROOT, 'templates')),
)
########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    # Default Django middleware.
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
)
########## END MIDDLEWARE CONFIGURATION


########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION


########## APP CONFIGURATION
DJANGO_APPS = (
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    # Useful template tags:
    # 'django.contrib.humanize',

    # Admin panel and documentation:
    'autocomplete_light',
    'suit',
    'django.contrib.admin',
    # 'django.contrib.admindocs',
    'django.contrib.humanize',
)

THIRD_PARTY_APPS = (
    # Database migration helpers:
    'south',
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
    'datetimewidget',
    'logentry_admin',
    'dbbackup',
    'leaflet',
    'djgeojson',
    'paintstore',
    'messages_extends',
    'corsheaders',

)

# Apps specific for this project go here.
LOCAL_APPS = (
    'funds',
    'locations',
    'activityinfo',
    'reports',
    'partners',
    'emails',
    'trips',
    'tpm',
    'users',
    'registration',
)

# SOUTH_MIGRATION_MODULES = {
#     "post_office": "post_office.south_migrations",
# }

MESSAGE_STORAGE = 'messages_extends.storages.FallbackStorage'

LEAFLET_CONFIG = {
    'TILES':  'http://otile1.mqcdn.com/tiles/1.0.0/map/{z}/{x}/{y}.jpg',
    'ATTRIBUTION_PREFIX': 'Tiles Courtesy of <a href="http://www.mapquest.com/" target="_blank">MapQuest</a> <img src="http://developer.mapquest.com/content/osm/mq_logo.png">',
    'DEFAULT_CENTER': (os.environ.get('MAP_LAT', 33.9), os.environ.get('MAP_LONG', 36)),
    'DEFAULT_ZOOM': int(os.environ.get('MAP_ZOOM', 9)),
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
}

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
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
    'root': {
        'handlers': ['console', ],
        'level': 'INFO'
    },
}
