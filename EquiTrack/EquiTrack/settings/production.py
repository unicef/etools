"""Production settings and globals."""

from base import *
from staging import environ


########## HOST CONFIGURATION
# See: https://docs.djangoproject.com/en/1.5/releases/1.5/#allowed-hosts-required-in-production
ALLOWED_HOSTS = [
    os.environ.get('DJANGO_ALLOWED_HOST', '127.0.0.1'),
]
########## END HOST CONFIGURATION

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

########## DATABASE CONFIGURATION
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        env="DATABASE_URL",
        default='postgis://db-user:@localhost:5432/equitrack'
    )
}
########## END DATABASE CONFIGURATION

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

SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY)

