from django.contrib.admin.sites import AdminSite

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.libraries.post_office.admin import EtoolsPostOfficeLogAdmin

from post_office.models import Log


class MockRequest:
    pass


class TestSnapshotAdmin(BaseTenantTestCase):

    def test_has_add_permission(self):
        adminSite = EtoolsPostOfficeLogAdmin(Log, AdminSite())
        self.assertFalse(adminSite.has_add_permission(MockRequest()))
