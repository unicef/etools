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

import datetime
import os
from os.path import abspath, basename, dirname, join, normpath

import dj_database_url
import yaml

import etools


# Helper function to convert strings (i.e. environment variable values) to a Boolean
def str2bool(value):
    """
    Given a string 'value', return a Boolean which that string represents.

    This assumes that 'value' is one of a list of some common possible Truthy string values.
    """
    return str(value).lower() in ("yes", "true", "t", "1")


# Absolute filesystem path to the Django project directory:
CONFIG_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
PACKAGE_ROOT = dirname(CONFIG_ROOT)
SITE_NAME = basename(CONFIG_ROOT)

# DJANGO CORE SETTINGS ################################
# organized per https://docs.djangoproject.com/en/1.9/ref/settings/#core-settings-topical-index

SECRETS_FILE_LOCATION = os.environ.get('SECRETS_FILE_LOCATION', join(CONFIG_ROOT, 'secrets.yml'))

try:
    with open(SECRETS_FILE_LOCATION, 'r') as secrets_file:
        SECRETS = yaml.load(secrets_file)['ENVIRONMENT']
except FileNotFoundError:
    # pass, for now we default trying to get the secrets from env vars as well
    SECRETS = {}


def get_from_secrets_or_env(var_name, default=None):
    """Attempts to get variables from secrets file, if it fails, tries env, returns default"""
    return SECRETS.get(var_name, os.environ.get(var_name, default))


# DJANGO: CACHE
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': get_from_secrets_or_env('REDIS_URL', 'redis://localhost:6379/0')
    }
}

# DJANGO: DATABASE
db_config = dj_database_url.config(
    default=get_from_secrets_or_env('DATABASE_URL', 'postgis:///etools')
)

ORIGINAL_BACKEND = 'django.contrib.gis.db.backends.postgis'
db_config['ENGINE'] = 'django_tenants.postgresql_backend'
db_config['CONN_MAX_AGE'] = 0
DATABASES = {
    'default': db_config
}
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# DJANGO: DEBUGGING
DEBUG = str2bool(get_from_secrets_or_env('DJANGO_DEBUG'))

# DJANGO: EMAIL
DEFAULT_FROM_EMAIL = "no-reply@unicef.org"
EMAIL_BACKEND = 'unicef_notification.backends.EmailBackend'
EMAIL_HOST = get_from_secrets_or_env('EMAIL_HOST', '')
EMAIL_HOST_USER = get_from_secrets_or_env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = get_from_secrets_or_env('EMAIL_HOST_PASSWORD', '')
EMAIL_PORT = get_from_secrets_or_env('EMAIL_HOST_PORT', 587)
EMAIL_USE_TLS = str2bool(get_from_secrets_or_env('EMAIL_USE_TLS'))  # set True if using TLS

# DJANGO: ERROR REPORTING

# DJANGO: FILE UPLOADS
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', '/tmp/etools/media/')
MEDIA_URL = '/media/'

# DJANGO: GLOBALIZATION (I18N/L10N)
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# DJANGO: HTTP
MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'etools.applications.EquiTrack.auth.CustomSocialAuthExceptionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'etools.applications.EquiTrack.middleware.EToolsTenantMiddleware',
    'waffle.middleware.WaffleMiddleware',  # needs request.tenant from EToolsTenantMiddleware
)
WSGI_APPLICATION = 'etools.config.wsgi.application'

# DJANGO: LOGGING
LOGGING = {
    'version': 1,
    'disable_existing_loggers': str2bool(get_from_secrets_or_env('DJANGO_DISABLE_EXISTING_LOGGERS', 'True')),
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
GDAL_LIBRARY_PATH = '/usr/lib/libgdal.so.20'
# DJANGO: MODELS
FIXTURE_DIRS = (
    os.path.join(os.path.dirname(etools.__file__), 'applications', 'EquiTrack', 'data'),
)
SHARED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django.contrib.postgres',
    'django.contrib.admin',
    'django.contrib.humanize',

    'storages',
    'rest_framework',
    'rest_framework_gis',
    'rest_framework_swagger',
    'rest_framework.authtoken',
    'drfpasswordless',
    'import_export',
    'gunicorn',
    'post_office',
    'django_celery_beat',
    'django_celery_results',
    'djcelery_email',
    'leaflet',
    'corsheaders',
    'mptt',
    'easy_pdf',
    'ordered_model',
    'social_django',
    'etools.applications.vision',
    'etools.applications.publics',
    # you must list the app where your tenant model resides in
    'etools.applications.users',
    'django_filters',
    'etools.applications.environment',
    'etools.applications.action_points.categories',
    'etools.applications.audit.purchase_order',
    'etools.applications.EquiTrack',
    'etools.applications.tpm.tpmpartners',
    'waffle',
    'etools.applications.permissions2',
    'unicef_notification',
)

TENANT_APPS = (
    'django_fsm',
    'django_comments',
    'logentry_admin',
    'etools.applications.funds',
    'unicef_locations',
    'etools.applications.reports',
    'etools.applications.partners',
    'etools.applications.hact',
    'etools.applications.activities',
    'etools.applications.t2f',
    'etools.applications.attachments',
    'etools.applications.tpm',
    'etools.applications.audit',
    'etools.applications.firms',
    'etools.applications.management',
    'etools.applications.action_points',
    'unicef_snapshot',
    'unicef_attachments',
)
INSTALLED_APPS = ('django_tenants',) + SHARED_APPS + TENANT_APPS

# DJANGO: SECURITY
ALLOWED_HOSTS = [
    get_from_secrets_or_env('DJANGO_ALLOWED_HOST', '127.0.0.1'), '0.0.0.0',
]
SECRET_KEY = r"j8%#f%3t@9)el9jh4f0ug4*mm346+wwwti#6(^@_ksf@&k^ob1"  # only used locally

# DJANGO: TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            normpath(join(PACKAGE_ROOT, 'templates')),
            normpath(join(PACKAGE_ROOT, 'templates', 'frontend'))
        ],
        'APP_DIRS': False,  # False because we set loaders manually below
        'OPTIONS': {
            'debug': DEBUG,
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'unicef_notification.loaders.EmailTemplateLoader',
            ],
            'context_processors': [
                # Already defined Django-related contexts here

                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',

            ],
        },
    },
]

# DJANGO: URLS
ROOT_URLCONF = 'etools.config.urls'


# Django Contrib Settings ################################

# CONTRIB: AUTH
AUTHENTICATION_BACKENDS = (
    # 'social_core.backends.azuread_b2c.AzureADB2COAuth2',
    'etools.applications.EquiTrack.auth.CustomAzureADBBCOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)
AUTH_USER_MODEL = 'users.User'
LOGIN_REDIRECT_URL = '/'

HOST = get_from_secrets_or_env('DJANGO_ALLOWED_HOST', 'http://localhost:8000/')
LOGIN_URL = LOGOUT_REDIRECT_URL = get_from_secrets_or_env('LOGIN_URL', '/landing/')

# CONTRIB: GIS (GeoDjango)
POSTGIS_VERSION = (2, 1)

# CONTRIB: SESSIONS
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# CONTRIB: SITES
SITE_ID = 1

# CONTRIB: STATIC FILES
STATIC_ROOT = os.environ.get('STATIC_ROOT', '/tmp/etools/static/')
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    normpath(join(PACKAGE_ROOT, 'assets')),
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)


# Third party library settings ################################

# django-post_office: https://github.com/ui/django-post_office
POST_OFFICE = {
    'DEFAULT_PRIORITY': 'now',
    'BACKENDS': {
        # Will ensure email is sent async
        'default': 'djcelery_email.backends.CeleryEmailBackend'
    }
}

# celery: http://docs.celeryproject.org/en/latest/userguide/configuration.html
CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'application/text']
CELERY_BROKER_URL = get_from_secrets_or_env('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_VISIBILITY_VAR = get_from_secrets_or_env('CELERY_VISIBILITY_TIMEOUT', 1800)  # in seconds
CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': int(CELERY_BROKER_VISIBILITY_VAR)}
CELERY_RESULT_BACKEND = 'django-db'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'
# Sensible settings for celery
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_PUBLISH_RETRY = True
CELERY_WORKER_DISABLE_RATE_LIMITS = False

# By default we will ignore result
# If you want to see results and try out tasks interactively, change it to False
# Or change this setting on tasks level

CELERY_IMPORTS = (
    'etools.applications.vision.tasks',
    'etools.applications.hact.tasks',
)

CELERY_TASK_IGNORE_RESULT = True
CELERY_SEND_TASK_ERROR_EMAILS = False
CELERY_RESULT_EXPIRES = 600
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# django-celery-email: https://github.com/pmclanahan/django-celery-email
CELERY_EMAIL_BACKEND = get_from_secrets_or_env('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
CELERY_TASK_ROUTES = {
    'etools.applications.vision.tasks.sync_handler': {'queue': 'vision_queue'},
    'etools.applications.hact.tasks.update_hact_for_country': {'queue': 'vision_queue'},
    'etools.libraries.azure_graph_api.tasks.sync_delta_users': {'queue': 'vision_queue'},
    'etools.libraries.azure_graph_api.tasks.sync_all_users': {'queue': 'vision_queue'}
}

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
        'etools.applications.EquiTrack.auth.EToolsTenantJWTAuthentication',
        'etools.applications.EquiTrack.auth.EtoolsTokenAuthentication',
    ),
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework_csv.renderers.CSVRenderer',
        'rest_framework_xml.renderers.XMLRenderer',
        'rest_framework.renderers.MultiPartRenderer',
    ),
    'DEFAULT_SCHEMA_CLASS': 'etools.applications.EquiTrack.inspectors.EToolsSchema',
}

# django-cors-headers: https://github.com/ottoyiu/django-cors-headers
CORS_ORIGIN_ALLOW_ALL = False

# django-rest-swagger: http://django-rest-swagger.readthedocs.io/en/latest/settings/
SWAGGER_SETTINGS = {
    'is_authenticated': True,
    'is_superuser': True,
}

# django-mptt: https://github.com/django-mptt/django-mptt
MPTT_ADMIN_LEVEL_INDENT = 20

# django-leaflet: django-leaflet
LEAFLET_CONFIG = {
    'TILES': 'http://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    'ATTRIBUTION_PREFIX': 'Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012',  # noqa
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
}

# django-tenant-schemas: https://github.com/bernardopires/django-tenant-schemas
TENANT_MODEL = "users.Country"
TENANT_DOMAIN_MODEL = "EquiTrack.Domain"

# don't call set search_path so much
# https://django-tenant-schemas.readthedocs.io/en/latest/use.html#performance-considerations
TENANT_LIMIT_SET_CALLS = True

# django-rest-framework-jwt: http://getblimp.github.io/django-rest-framework-jwt/
JWT_AUTH = {
    'JWT_ENCODE_HANDLER':
    'rest_framework_jwt.utils.jwt_encode_handler',

    'JWT_DECODE_HANDLER':
    'rest_framework_jwt.utils.jwt_decode_handler',

    'JWT_PAYLOAD_HANDLER':
    'rest_framework_jwt.utils.jwt_payload_handler',

    'JWT_PAYLOAD_GET_USER_ID_HANDLER':
    'rest_framework_jwt.utils.jwt_get_user_id_from_payload_handler',

    'JWT_PAYLOAD_GET_USERNAME_HANDLER':
    'rest_framework_jwt.utils.jwt_get_username_from_payload_handler',

    'JWT_RESPONSE_PAYLOAD_HANDLER':
    'rest_framework_jwt.utils.jwt_response_payload_handler',

    'JWT_ALGORITHM': 'HS256',
    'JWT_VERIFY': True,
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_LEEWAY': 30,
    'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=30000),
    'JWT_AUDIENCE': None,
    'JWT_ISSUER': None,

    'JWT_ALLOW_REFRESH': False,
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),

    'JWT_AUTH_HEADER_PREFIX': 'JWT',
}


# eTools settings ################################

ENVIRONMENT = get_from_secrets_or_env('ENVIRONMENT', '')

INACTIVE_BUSINESS_AREAS = get_from_secrets_or_env('INACTIVE_BUSINESS_AREAS', '').split(',')
if INACTIVE_BUSINESS_AREAS == ['']:
    # 'split' splits an empty string into an array with one empty string, which isn't
    # really what we want
    INACTIVE_BUSINESS_AREAS = []

SLACK_URL = get_from_secrets_or_env('SLACK_URL')

TASK_ADMIN_USER = get_from_secrets_or_env('TASK_ADMIN_USER', 'etools_task_admin')

VISION_URL = get_from_secrets_or_env('VISION_URL', 'http://invalid_vision_url')
VISION_USER = get_from_secrets_or_env('VISION_USER', 'invalid_vision_user')
VISION_PASSWORD = get_from_secrets_or_env('VISION_PASSWORD', 'invalid_vision_password')


# ALLOW BASIC AUTH FOR DEMO SITE
ALLOW_BASIC_AUTH = get_from_secrets_or_env('ALLOW_BASIC_AUTH', False)
if ALLOW_BASIC_AUTH:
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += (
        'etools.applications.EquiTrack.auth.DRFBasicAuthMixin',
    )

ISSUE_CHECKS = [
    'etools.applications.management.issues.project_checks.ActivePCANoSignedDocCheck',
    'etools.applications.management.issues.project_checks.PdOutputsWrongCheck',
    'etools.applications.management.issues.project_checks.InterventionsAssociatedSSFACheck',
    'etools.applications.management.issues.project_checks.InterventionsAreValidCheck',
    'etools.applications.management.issues.project_checks.PDAmendmentsMissingFilesCheck',
    'etools.applications.management.issues.project_checks.PCAAmendmentsMissingFilesCheck',
]

EMAIL_FOR_USER_RESPONSIBLE_FOR_INVESTIGATION_ESCALATIONS = get_from_secrets_or_env(
    'EMAIL_FOR_USER_RESPONSIBLE_FOR_INVESTIGATION_ESCALATIONS', 'integrity1@unicef.org'
)

AZURE_CLIENT_ID = get_from_secrets_or_env('AZURE_CLIENT_ID', 'invalid_azure_client_id')
AZURE_CLIENT_SECRET = get_from_secrets_or_env('AZURE_CLIENT_SECRET', 'invalid_azure_client_secret')
AZURE_TOKEN_URL = 'https://login.microsoftonline.com/unicef.org/oauth2/token'
AZURE_GRAPH_API_BASE_URL = 'https://graph.microsoft.com'
AZURE_GRAPH_API_VERSION = 'beta'
AZURE_GRAPH_API_PAGE_SIZE = 250

# drfpaswordless: https://github.com/aaronn/django-rest-framework-passwordless

PASSWORDLESS_AUTH = {
    # we can't use email here, because to_alias field length is 40, while email can be up to 254 symbols length.
    # with custom user model we can avoid this a bit tricky with custom property like cropped_email,
    # but for contrib user there is nothing better than use field having appropriate max length.
    # username is better choice as it can be only 30 symbols max and unique.
    'PASSWORDLESS_USER_EMAIL_FIELD_NAME': 'username'
}


KEY = os.getenv('AZURE_B2C_CLIENT_ID', None)
SECRET = os.getenv('AZURE_B2C_CLIENT_SECRET', None)

SOCIAL_AUTH_URL_NAMESPACE = 'social'
SOCIAL_AUTH_SANITIZE_REDIRECTS = False
SOCIAL_AUTH_POSTGRES_JSONFIELD = True
POLICY = os.getenv('AZURE_B2C_POLICY_NAME', "b2c_1A_UNICEF_PARTNERS_signup_signin")

TENANT_ID = os.getenv('AZURE_B2C_TENANT', 'unicefpartners.onmicrosoft.com')
SCOPE = ['openid', 'email']
IGNORE_DEFAULT_SCOPE = True
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email']
# In case we decide to whitelist:
# SOCIAL_AUTH_WHITELISTED_DOMAINS = ['unicef.org', 'google.com', 'ravdev.com']
LOGIN_ERROR_URL = "/workspace_inactive"
JWT_LEEWAY = 1000

SOCIAL_PASSWORD_RESET_POLICY = os.getenv('AZURE_B2C_PASS_RESET_POLICY', "B2C_1_PasswordResetPolicy")
SOCIAL_AUTH_PIPELINE = (
    # 'social_core.pipeline.social_auth.social_details',
    'etools.applications.EquiTrack.auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    # allows based on emails being listed in 'WHITELISTED_EMAILS' or 'WHITELISTED_DOMAINS'
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    # 'social_core.pipeline.user.get_username',
    'etools.applications.EquiTrack.auth.get_username',
    'social_core.pipeline.social_auth.associate_by_email',
    'etools.applications.EquiTrack.auth.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'etools.applications.EquiTrack.auth.user_details',
)

REPORT_EMAILS = get_from_secrets_or_env('REPORT_EMAILS', 'etools@unicef.org').replace(' ', '').split(',')

# email auth settings
EMAIL_AUTH_TOKEN_NAME = os.getenv('EMAIL_AUTH_TOKEN_NAME', 'url_auth_token')
SILENCED_SYSTEM_CHECKS = ["django_tenants.W003"]

# GET parameter that allows override of schema
SCHEMA_OVERRIDE_PARAM = "schema"

# Number of days before PCA required notification
PCA_REQUIRED_NOTIFICATION_LEAD = 30

UNICEF_NOTIFICATION_TEMPLATE_DIR = "notifications"
UNICEF_LOCATIONS_GET_CACHE_KEY = 'etools.libraries.locations.views.cache_key'

ATTACHMENT_FILEPATH_PREFIX_FUNC = "etools.applications.attachments.utils.get_filepath_prefix"
ATTACHMENT_FLAT_MODEL = "etools.applications.attachments.models.AttachmentFlat"
ATTACHMENT_DENORMALIZE_FUNC = "etools.applications.attachments.utils.denormalize_attachment"

GEOS_LIBRARY_PATH = os.getenv('GEOS_LIBRARY_PATH', '/usr/lib/libgeos_c.so.1')  # default path
GDAL_LIBRARY_PATH = os.getenv('GDAL_LIBRARY_PATH', '/usr/lib/libgdal.so.20')  # default path
