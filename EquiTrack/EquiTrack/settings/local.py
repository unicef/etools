from local_base import *

########## TOOLBAR CONFIGURATION
# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INSTALLED_APPS += (
    'debug_toolbar',
    'django_extensions',
)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INTERNAL_IPS = ('127.0.0.1',)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TEMPLATE_CONTEXT': True,
}
########## END TOOLBAR CONFIGURATION

POST_OFFICE = {
    'DEFAULT_PRIORITY': 'now',
    'BACKENDS': {
        # Will ensure email is sent async
        'default': 'django.core.mail.backends.console.EmailBackend'
    }
}

AZURE_ACCOUNT_NAME = os.environ.get('AZURE_ACCOUNT_NAME', None)
AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY', None)
AZURE_CONTAINER = os.environ.get('AZURE_CONTAINER', None)
AZURE_SSL = True
AZURE_AUTO_SIGN = True  # flag for automatically signing urls
AZURE_ACCESS_POLICY_EXPIRY = 120  # length of time before signature expires in seconds
AZURE_ACCESS_POLICY_PERMISSION = 'r'  # read permission

CORS_ORIGIN_ALLOW_ALL = False

if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY and AZURE_CONTAINER:

    DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
    # MEDIA_URL = 'https://{}.blob.core.windows.net/{}/'.format(
    #     AZURE_ACCOUNT_NAME, AZURE_CONTAINER
    # )