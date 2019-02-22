from django.contrib.admin.sites import AdminSite

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.libraries.snapshot.admin import EtoolsSnapshotActivityAdmin

from unicef_snapshot.models import Activity


class MockRequest:
    pass


class TestSnapshotAdmin(BaseTenantTestCase):

    def test_has_add_permission(self):
        adminSite = EtoolsSnapshotActivityAdmin(Activity, AdminSite())
        self.assertFalse(adminSite.has_add_permission(MockRequest()))
