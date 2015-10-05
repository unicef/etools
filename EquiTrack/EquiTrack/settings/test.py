from local import *

# TODO: Can be removed when we upgrade to 1.8
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# This has to be set to this particular backend in order for django to grab email and expose in tests
POST_OFFICE_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

