from local import *

########## TEST SETTINGS
# TEST_RUNNER = 'discover_runner.DiscoverRunner'
# TEST_DISCOVER_TOP_LEVEL = SITE_ROOT
# TEST_DISCOVER_ROOT = SITE_ROOT
# TEST_DISCOVER_PATTERN = "test_*.py"

########## DATABASE CONFIGURATION
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        env="WERCKER_POSTGRESQL_URL",
        default='postgis://localhost:5432/equitrack'
    )
}
########## END DATABASE CONFIGURATION

SOUTH_TESTS_MIGRATE = False

INSTALLED_APPS += (
    'django_nose',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'