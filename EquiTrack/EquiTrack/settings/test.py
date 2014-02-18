from local import *

########## TEST SETTINGS
# TEST_RUNNER = 'discover_runner.DiscoverRunner'
# TEST_DISCOVER_TOP_LEVEL = SITE_ROOT
# TEST_DISCOVER_ROOT = SITE_ROOT
# TEST_DISCOVER_PATTERN = "test_*.py"

SOUTH_TESTS_MIGRATE = False

INSTALLED_APPS += (
    'django_nose',
)

#TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'