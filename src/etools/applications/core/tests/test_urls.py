from django.conf import settings
from django.urls import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.urlresolvers import build_frontend_url
from etools.applications.users.tests.factories import UserFactory


class TestFrontendUrl(BaseTenantTestCase):
    def test_staff_user_url(self):
        self.assertIn(
            settings.HOST + reverse('main'),
            build_frontend_url('test', user=UserFactory(is_staff=True))
        )

    def test_common_user_url(self):
        self.assertIn(settings.HOST, build_frontend_url('test', user=UserFactory(is_staff=False)))
