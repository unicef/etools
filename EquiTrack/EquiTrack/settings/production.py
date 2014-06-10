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
    'dsn': 'https://02b60c5ae099494d8ffe93d1701f9448:d55afaa1a9cb498180f112e41deb34e9@app.getsentry.com/20023',
}

INSTALLED_APPS = INSTALLED_APPS + (
    'raven.contrib.django.raven_compat',
)

MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (
    'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
)

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', None)
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', None)

if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
    # use S3 for file storage if all AWS settings are set in this environment
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
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


########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
MANDRILL_API_KEY = os.environ.get("MANDRILL_KEY", '')
POST_OFFICE_BACKEND = "djrill.mail.backends.djrill.DjrillBackend"
EMAIL_BACKEND = 'post_office.EmailBackend'
########## END EMAIL CONFIGURATION


SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY)

