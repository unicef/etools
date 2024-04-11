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

from django.db import connection
from django.utils.translation import gettext_lazy as _

import dj_database_url
import sentry_sdk
import yaml
from sentry_sdk import configure_scope
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

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
        SECRETS = yaml.safe_load(secrets_file)['ENVIRONMENT']
except FileNotFoundError:
    # pass, for now we default trying to get the secrets from env vars as well
    SECRETS = {}


def get_from_secrets_or_env(var_name, default=None):
    """Attempts to get variables from secrets file, if it fails, tries env, returns default"""
    return SECRETS.get(var_name, os.environ.get(var_name, default))


# DJANGO: CACHE
CACHES = {
    'default': {
        'BACKEND': 'etools.libraries.redis_cache.base.eToolsCache',
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

# user that can update other user credentials via api
SERVICE_NOW_USER = get_from_secrets_or_env('SERVICE_NOW_USER', 'api_servicenow_etools@unicef.org')

# DJANGO: EMAIL
DEFAULT_FROM_EMAIL = get_from_secrets_or_env('DEFAULT_FROM_EMAIL', "no-reply@unicef.org")
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
LANGUAGES = [
    ('en', _('English')),
    ('fr', _('Français')),
    ('ru', _('Russian')),
    ('pt', _('Portuguese')),
    ('es', _('Spanish')),
    ('ar', _('Arabic')),
]

TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# DJANGO: HTTP
MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'etools.applications.core.auth.CustomSocialAuthExceptionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'etools.applications.core.middleware.EToolsTenantMiddleware',
    'waffle.middleware.WaffleMiddleware',  # needs request.tenant from EToolsTenantMiddleware
    'etools.applications.core.middleware.EToolsLocaleMiddleware',
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

# DJANGO: MODELS
FIXTURE_DIRS = (
    os.path.join(os.path.dirname(etools.__file__), 'applications', 'core', 'data'),
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
    'django_extensions',
    'storages',
    'rest_framework',
    'rest_framework_gis',
    'rest_framework_swagger',
    'rest_framework.authtoken',
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
    'admin_extra_urls',
    'etools.applications.vision',
    'etools.applications.publics',
    'etools.applications.users',
    'django_filters',
    'etools.applications.environment',
    'etools.applications.action_points.categories',
    'etools.applications.audit.purchase_order',
    'etools.applications.core',
    'etools.applications.tpm.tpmpartners',
    'waffle',
    'etools.applications.permissions2',
    'unicef_notification',
    'etools_offline',
    'etools.applications.offline',
    'etools.applications.organizations',
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
    'etools.applications.locations',
    'etools.applications.management',
    'etools.applications.action_points',
    'etools.applications.psea',
    'etools.applications.field_monitoring.fm_settings',
    'etools.applications.field_monitoring.planning',
    'etools.applications.field_monitoring.data_collection',
    'etools.applications.field_monitoring.analyze',
    'etools.applications.comments',
    'etools.applications.travel',
    'etools.applications.ecn',
    'unicef_snapshot',
    'unicef_attachments',
    'unicef_vision',
    'etools.applications.last_mile'
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
        ],
        'APP_DIRS': False,  # False because we set loaders manually below
        'OPTIONS': {
            'debug': DEBUG,
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                    'unicef_notification.loaders.EmailTemplateLoader',
                ]),
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
    'etools.applications.core.auth.CustomAzureADBBCOAuth2',
    'etools.applications.core.auth.eToolsModelBackend',
)
AUTH_USER_MODEL = 'users.User'
LOGIN_REDIRECT_URL = '/'

HOST = get_from_secrets_or_env('DJANGO_ALLOWED_HOST', 'http://localhost:8082')

LOGIN_URL = LOGOUT_REDIRECT_URL = get_from_secrets_or_env('LOGIN_URL', '/landing/')

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

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
# CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'default'
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
        'etools.applications.core.auth.EToolsTenantJWTAuthentication',
        'etools.applications.core.auth.eToolsOLCTokenAuth',
        'etools.applications.core.auth.EtoolsTokenAuthentication',
    ),
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework_csv.renderers.CSVRenderer',
        'rest_framework_xml.renderers.XMLRenderer',
        'rest_framework.renderers.MultiPartRenderer',
    ),
    'DEFAULT_SCHEMA_CLASS': 'etools.applications.core.inspectors.EToolsSchema',
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
TENANT_DOMAIN_MODEL = "core.Domain"

# don't call set search_path so much
# https://django-tenant-schemas.readthedocs.io/en/latest/use.html#performance-considerations
TENANT_LIMIT_SET_CALLS = True

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': datetime.timedelta(minutes=480),
    'REFRESH_TOKEN_LIFETIME': datetime.timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': SECRET_KEY,
    'AUDIENCE': None,
    'ISSUER': None,
    'LEEWAY': 60,

    'AUTH_HEADER_TYPES': ('JWT',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'pk',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_jwt_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': datetime.timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': datetime.timedelta(days=1),
}

SENTRY_DSN = get_from_secrets_or_env('SENTRY_DSN')  # noqa: F405

if SENTRY_DSN:
    def before_send(event, hint):
        with configure_scope() as scope:
            scope.set_extra("tenant", connection.tenant.schema_name)

        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # by default this is False, must be set to True so the library attaches the request data to the event
        send_default_pii=True,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        before_send=before_send,
    )


# eTools settings ################################

ENVIRONMENT = get_from_secrets_or_env('ENVIRONMENT', '')

INACTIVE_BUSINESS_AREAS = get_from_secrets_or_env('INACTIVE_BUSINESS_AREAS', '').split(',')
if INACTIVE_BUSINESS_AREAS == ['']:
    # 'split' splits an empty string into an array with one empty string, which isn't
    # really what we want
    INACTIVE_BUSINESS_AREAS = []

SLACK_URL = get_from_secrets_or_env('SLACK_URL')

TASK_ADMIN_USER = get_from_secrets_or_env('TASK_ADMIN_USER', 'etools_task_admin@unicef.org')

INSIGHT_LOGGER_MODEL = "vision.VisionSyncLog"
INSIGHT_SUB_KEY = get_from_secrets_or_env('INSIGHT_SUB_KEY', 'invalid_key')
INSIGHT_URL = get_from_secrets_or_env('INSIGHT_URL', 'http://invalid_vision_url')
INSIGHT_BANK_KEY = get_from_secrets_or_env('INSIGHT_BANK_KEY', None)

# Vision data uploader
EZHACT_PD_VISION_URL = get_from_secrets_or_env('EZHACT_PD_VISION_URL', '')  # example: http://172.18.0.1:8083/upload/pd/
EZHACT_API_USER = get_from_secrets_or_env('EZHACT_API_USER', '')
EZHACT_API_PASSWORD = get_from_secrets_or_env('EZHACT_API_PASSWORD', '')
EZHACT_INTEGRATION_DISABLED = bool(get_from_secrets_or_env('EZHACT_INTEGRATION_DISABLED', False))
EZHACT_CERT_PATH = os.path.join(CONFIG_ROOT, 'keys/vision/ezhact_cert.pem')
EZHACT_KEY_PATH = os.path.join(CONFIG_ROOT, 'keys/vision/ezhact_key.pem')

# ALLOW BASIC AUTH FOR DEMO SITE
ALLOW_BASIC_AUTH = get_from_secrets_or_env('ALLOW_BASIC_AUTH', False)
if ALLOW_BASIC_AUTH:
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += (
        'etools.applications.core.auth.DRFBasicAuthMixin',
    )

EMAIL_FOR_USER_RESPONSIBLE_FOR_INVESTIGATION_ESCALATIONS = get_from_secrets_or_env(
    'EMAIL_FOR_USER_RESPONSIBLE_FOR_INVESTIGATION_ESCALATIONS', 'integrity1@unicef.org'
)

AZURE_CLIENT_ID = get_from_secrets_or_env('AZURE_CLIENT_ID', 'invalid_azure_client_id')
AZURE_CLIENT_SECRET = get_from_secrets_or_env('AZURE_CLIENT_SECRET', 'invalid_azure_client_secret')
AZURE_TOKEN_URL = 'https://login.microsoftonline.com/unicef.org/oauth2/token'
AZURE_GRAPH_API_BASE_URL = 'https://graph.microsoft.com'
AZURE_GRAPH_API_VERSION = 'beta'
AZURE_GRAPH_API_PAGE_SIZE = 250

KEY = os.getenv('AZURE_B2C_CLIENT_ID', None)
SECRET = os.getenv('AZURE_B2C_CLIENT_SECRET', None)

SOCIAL_AUTH_URL_NAMESPACE = 'social'
SOCIAL_AUTH_SANITIZE_REDIRECTS = False
SOCIAL_AUTH_JSONFIELD_ENABLED = True
POLICY = os.getenv('AZURE_B2C_POLICY_NAME', "b2c_1A_UNICEF_PARTNERS_signup_signin")

TENANT_ID = os.getenv('AZURE_B2C_TENANT', 'unicefpartners')
TENANT_B2C_URL = f'{TENANT_ID}.b2clogin.com'

SCOPE = ['openid', 'email']
IGNORE_DEFAULT_SCOPE = True
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email']
# In case we decide to whitelist:
# SOCIAL_AUTH_WHITELISTED_DOMAINS = ['unicef.org', 'google.com', 'ravdev.com']
LOGIN_ERROR_URL = "/workspace_inactive"

SOCIAL_LOGOUT_URL = f'https://{TENANT_B2C_URL}/{TENANT_ID}.onmicrosoft.com/{POLICY}/oauth2/v2.0/logout' \
                    f'?post_logout_redirect_uri={HOST}/logout/'


SOCIAL_PASSWORD_RESET_POLICY = os.getenv('AZURE_B2C_PASS_RESET_POLICY', "B2C_1_PasswordResetPolicy")
SOCIAL_AUTH_PIPELINE = (
    # 'social_core.pipeline.social_auth.social_details',
    'etools.applications.core.auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    # allows based on emails being listed in 'WHITELISTED_EMAILS' or 'WHITELISTED_DOMAINS'
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    # 'social_core.pipeline.user.get_username',
    'etools.applications.core.auth.get_username',
    'social_core.pipeline.social_auth.associate_by_email',
    'etools.applications.core.auth.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'etools.applications.core.auth.user_details',
)

REPORT_EMAILS = get_from_secrets_or_env('REPORT_EMAILS', 'etools@unicef.org').replace(' ', '').split(',')

# email auth settings
EMAIL_AUTH_TOKEN_NAME = os.getenv('EMAIL_AUTH_TOKEN_NAME', 'url_auth_token')
SILENCED_SYSTEM_CHECKS = ["django_tenants.W003"]

# GET parameter that allows override of schema
SCHEMA_OVERRIDE_PARAM = "schema"

# Number of days before PCA required notification
PCA_REQUIRED_NOTIFICATION_LEAD = 30
PCA_SKIP_FINANCIAL_DATA = get_from_secrets_or_env('PCA_SKIP_FINANCIAL_DATA', False)

UNICEF_NOTIFICATION_TEMPLATE_DIR = "notifications"
UNICEF_LOCATIONS_GET_CACHE_KEY = 'etools.applications.locations.views.cache_key'

ATTACHMENT_FILEPATH_PREFIX_FUNC = "etools.applications.attachments.utils.get_filepath_prefix"
ATTACHMENT_FLAT_MODEL = "etools.applications.attachments.models.AttachmentFlat"
ATTACHMENT_DENORMALIZE_FUNC = "etools.applications.attachments.utils.denormalize_attachment"
ATTACHMENT_PERMISSIONS = "etools.applications.attachments.permissions.IsInSchema"
ATTACHMENT_INVALID_FILE_TYPES = [
    "application/json",
    "application/x-msdownload",
    "applications/x-ms-installer",
    "application/x-sh",
    "text/x-perl",
    "text/x-python",
    "text/x-script.python",
    "application/x-bytecode.python",
    "text/javascript",
    "application/x-typescript",
    "text/x.typescript",
    "text/prs.typescript",
    # archive files
    "application/x-bzip",
    "application/x-bzip2",
    "application/gzip",
    "application/java-archive",
    "application/x-httpd-php",
    "application/vnd.rar",
    "application/x-tar",
    "application/zip",
    "application/x-7z-compressed",
]

GEOS_LIBRARY_PATH = os.getenv('GEOS_LIBRARY_PATH', '/usr/lib/libgeos_c.so.1')  # default path
GDAL_LIBRARY_PATH = os.getenv('GDAL_LIBRARY_PATH', '/usr/lib/libgdal.so.28')  # default path

SHELL_PLUS_PRE_IMPORTS = (
    ('etools.applications.core.util_scripts', '*'),
)

UNICEF_USER_EMAIL = "@unicef.org"
PSEA_ASSESSMENT_FINAL_RECIPIENTS = get_from_secrets_or_env(
    'PSEA_ASSESSMENT_FINAL_RECIPIENTS',
    '',
).split(',')

INSIGHT_REQUESTS_TIMEOUT = get_from_secrets_or_env('INSIGHT_REQUESTS_TIMEOUT', 400)  # in seconds

# Etools offline collect
# https://github.com/unicef/etools-offline-collect/blob/develop/client/README.md
ETOOLS_OFFLINE_API = get_from_secrets_or_env('ETOOLS_OFFLINE_API', '')
ETOOLS_OFFLINE_TOKEN = get_from_secrets_or_env('ETOOLS_OFFLINE_TOKEN', '')
ETOOLS_OFFLINE_TASK_APP = "etools.config.celery.get_task_app"

UNICEF_LOCATIONS_MODEL = 'locations.Location'

# PRP Integration
# https://github.com/unicef/etools-partner-reporting-portal
PRP_API_ENDPOINT = get_from_secrets_or_env('PRP_API_ENDPOINT', '')  # example: http://172.18.0.1:8083/api
PRP_API_USER = get_from_secrets_or_env('PRP_API_USER', '')
PRP_USER_SYNC_DELAY = int(get_from_secrets_or_env('PRP_USER_SYNC_DELAY', 5))


# EPD settings
PMP_V2_RELEASE_DATE = get_from_secrets_or_env('PMP_PD_V2_RELEASE_DATE', '2020-10-01')
PMP_V2_RELEASE_DATE = datetime.datetime.strptime(PMP_V2_RELEASE_DATE, '%Y-%m-%d').date()


# ECN Integration
# https://github.com/unicef/etools-ecn
ECN_API_ENDPOINT = get_from_secrets_or_env('ECN_API_ENDPOINT', '')  # example: http://172.18.0.1:8086/api

# Emails allowed to edit admin models in Partners and Reports apps
ADMIN_EDIT_EMAILS = get_from_secrets_or_env('ADMIN_EDIT_EMAILS', '')


# Stale non-UNICEF users deactivation threshold
STALE_USERS_DEACTIVATION_THRESHOLD_DAYS = int(
    get_from_secrets_or_env('STALE_USERS_DEACTIVATION_THRESHOLD_DAYS', 3 * 30)
)

WAYBILL_EMAILS = get_from_secrets_or_env('WAYBILL_EMAILS', '')


RUTF_MATERIALS = get_from_secrets_or_env('RUTF_MATERIALS', '').split(',')
