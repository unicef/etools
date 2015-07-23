from local import *

SOUTH_TESTS_MIGRATE = False
SKIP_SOUTH_TESTS = True

# This has to be set to this particular backend in order for django to grab emails and expose them in tests
POST_OFFICE_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

