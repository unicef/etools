from base import *  # noqa

ALLOWED_HOSTS = ['127.0.0.1']
# This has to be set to this particular backend in order for django to grab email and expose in tests
POST_OFFICE['BACKENDS']['default'] = 'django.core.mail.backends.locmem.EmailBackend'  # noqa

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]


class DisableMigrations(object):

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return "notmigrations"

# MIGRATION_MODULES = DisableMigrations()

# MIGRATION_MODULES = dict((app, '%s.fake_migrations' % app) for app in INSTALLED_APPS)
# MIGRATION_MODULES = dict((app, None) for app in INSTALLED_APPS)


TEST_RUNNER = 'EquiTrack.tests.runners.TestRunner'
