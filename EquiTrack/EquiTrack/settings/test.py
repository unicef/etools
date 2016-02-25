from local import *


# This has to be set to this particular backend in order for django to grab email and expose in tests
POST_OFFICE['BACKENDS']['default'] = 'django.core.mail.backends.locmem.EmailBackend'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]


class DisableMigrations(object):

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return "notmigrations"

MIGRATION_MODULES = {'partners': 'partners.test.test_migrations'}
