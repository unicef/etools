from django.db import connection

from etools.applications.audit.tests.factories import UserFactory
from etools.libraries.djangolib.models import GroupWrapper


class FMBaseTestCaseMixin(object):
    def setUp(self):
        super(FMBaseTestCaseMixin, self).setUp()
        GroupWrapper.invalidate_instances()

        self.unicef_user = UserFactory(first_name='UNICEF User', unicef_user=True,
                                       profile__countries_available=[connection.tenant])
        self.usual_user = UserFactory(first_name='Unknown user',
                                      profile__countries_available=[connection.tenant])
