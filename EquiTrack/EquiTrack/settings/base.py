"""Common settings and globals."""

import os
from os.path import abspath, basename, dirname, join, normpath
from sys import path


########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# for Django 1.6
BASE_DIR = SITE_ROOT

# Site name:
SITE_NAME = basename(DJANGO_ROOT)
SUIT_CONFIG = {
    'ADMIN_NAME': 'EquiTrack',
    'SEARCH_URL': '/admin/partners/pca/',

    'MENU': (

        {'label': 'PCAs', 'icon': 'icon-pencil', 'models': [
            {'model': 'partners.pca', 'label': 'List of PCAs'},
            {'model': 'partners.partnerorganization', 'label': 'Partners'},
        ]},

        {'app': 'funds', 'icon': 'icon-briefcase'},

        {'label': 'Result Structures', 'app': 'reports', 'icon': 'icon-info-sign'},

        {'label': 'Locations', 'icon': 'icon-globe', 'models': [
            {'label': 'Governorate', 'model': 'locations.governorate'},
            {'label': 'Cazas', 'model': 'locations.region'},
            {'label': 'Localitys', 'model': 'locations.locality'},
            {'label': 'Gateways', 'model': 'locations.gatewaytype'},
            {'label': 'Locations', 'model': 'locations.location'},
        ]},

        {'app': 'filer', 'label': 'Files', 'icon': 'icon-file'},
    )
}

LOGIN_URL = '/login/'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    )
}
# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)
########## END PATH CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION


########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('James Cranwell-Ward', 'jcranwellwardl@unicef.org'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
########## END DATABASE CONFIGURATION


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

#DATE_INPUT_FORMATS = (
#    '%d-%m-%Y',
#    '%Y-%m-%d',
#    '%d/%m/%Y',
#    '%d/%m/%y',
#    '%m/%d/%Y',
#    '%m/%d/%y',
#    '%b %d %Y',
#    '%b %d, %Y',
#    '%d %b %Y',
#    '%d %b, %Y',
#    '%B %d %Y',
#    '%B %d, %Y',
#    '%d %B %Y',
#    '%d %B, %Y'
#)
########## END GENERAL CONFIGURATION


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(SITE_ROOT, 'media'))

####### S3 Storage setup ########
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'

# Use Amazon S3 for static files storage.
STATICFILES_STORAGE = "require_s3.storage.OptimizedCachedStaticFilesStorage"

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_AUTO_CREATE_BUCKET = True
AWS_HEADERS = {
    "Cache-Control": "public, max-age=86400",
}
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = False
AWS_S3_SECURE_URLS = True
AWS_REDUCED_REDUNDANCY = False
AWS_IS_GZIPPED = False

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = 'https://{}.s3.amazonaws.com/'.format(AWS_STORAGE_BUCKET_NAME)
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
########## END MEDIA CONFIGURATION


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(SITE_ROOT, 'assets'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'static')),
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

    #'grappelli.dashboard',
    #'grappelli',
    #'nested_inlines',
    'autocomplete_light',
    'suit',
    'django.contrib.admin',
    # 'django.contrib.admindocs',
)

THIRD_PARTY_APPS = (
    # Database migration helpers:
    'south',
    'gunicorn',
    'filer',
    'easy_thumbnails',
    'storages',
    'reversion',
    'rest_framework',
    'import_export',
    'smart_selects',
    'herokuapp',
)

# Apps specific for this project go here.
LOCAL_APPS = (
    'funds',
    'reports',
    'locations',
    'tracker',
    'partners',

)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
########## END APP CONFIGURATION


########## LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
########## END LOGGING CONFIGURATION


########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = '%s.wsgi.application' % SITE_NAME
########## END WSGI CONFIGURATION
