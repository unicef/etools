__author__ = 'jcranwellward'

from os import environ
from urlparse import urlparse

from base import *

# Load the Heroku environment.
from herokuapp.env import load_env
load_env(__file__, "equitrack")

# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django.core.exceptions import ImproperlyConfigured


def get_env_setting(setting):
    """ Get the environment setting or return exception """
    try:
        return environ[setting]
    except KeyError:
        error_msg = "Set the %s env variable" % setting
        raise ImproperlyConfigured(error_msg)

########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', False)

if isinstance(DEBUG, str):
    if DEBUG.lower() == "true":
        DEBUG = True
    else:
        DEBUG = False

TEMPLATE_DEBUG = DEBUG

DEBUG = False

RAVEN_CONFIG = {
    'dsn': 'https://edc3cc4bf9004598aeda1e452b71e256:27801a505ae245c78464711084442fc2@app.getsentry.com/17066',
}

INSTALLED_APPS = INSTALLED_APPS + (
    'raven.contrib.django.raven_compat',
    'herokuapp',
)
########## END DEBUG CONFIGURATION

SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY)

ALLOWED_HOSTS = ['equitrack.herokuapp.com', 'equitrack.uniceflebanon.org']

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION

####### S3 Storage setup ########
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'

# Use Amazon S3 for static files storage.
STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'

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
STATIC_URL = 'https://{}.s3.amazonaws.com/'.format(AWS_STORAGE_BUCKET_NAME)

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

########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
import dj_database_url
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        env="DATABASE_URL",
        default='postgis://db-user:@localhost:5432/equitrack'
    )
}
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
REDIS_URL = os.environ.get('REDISCLOUD_URL', 'redis://localhost/')
redis_url = urlparse(REDIS_URL)

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': '{0}:{1}'.format(redis_url.hostname, redis_url.port),
        'OPTIONS': {
            'DB': 0,
            'PASSWORD': redis_url.password,
            'PARSER_CLASS': 'redis.connection.HiredisParser'
        },
    },
    # Long cache timeout for staticfiles, since this is used heavily by the optimizing storage.
    "staticfiles": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": 60 * 60 * 24 * 365,
        "LOCATION": "staticfiles",
    },
}
########## END CACHE CONFIGURATION
