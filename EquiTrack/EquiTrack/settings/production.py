"""Production settings and globals."""

from os import environ
from base import *


########## HOST CONFIGURATION
# See: https://docs.djangoproject.com/en/1.5/releases/1.5/#allowed-hosts-required-in-production
ALLOWED_HOSTS = [
    os.environ.get('DJANGO_ALLOWED_HOST', '127.0.0.1'),
]
########## END HOST CONFIGURATION

########## DATABASE CONFIGURATION
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        env="DATABASE_URL",
        default='postgis://localhost:5432/equitrack'
    )
}
########## END DATABASE CONFIGURATION

# Sentry config
RAVEN_CONFIG = {
    'dsn': 'https://02b60c5ae099494d8ffe93d1701f9448:d55afaa1a9cb498180f112e41deb34e9@app.getsentry.com/20023',
}

INSTALLED_APPS = INSTALLED_APPS + (
    'raven.contrib.django.raven_compat',
)

MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (
  'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
)

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
MEDIA_URL = 'https://{}.s3.amazonaws.com/'.format(AWS_STORAGE_BUCKET_NAME)
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

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = environ.get('EMAIL_HOST', 'smtp.gmail.com')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-password
EMAIL_HOST_PASSWORD = environ.get('EMAIL_HOST_PASSWORD', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
EMAIL_HOST_USER = environ.get('EMAIL_HOST_USER', 'your_email@example.com')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = environ.get('EMAIL_PORT', 587)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-use-tls
EMAIL_USE_TLS = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = EMAIL_HOST_USER
########## END EMAIL CONFIGURATION

SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY)

