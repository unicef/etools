from __future__ import unicode_literals

from django.db import connection

from EquiTrack.tests.mixins import APITenantTestCase, VCR
from publics.models import WBS, Grant, Fund
from publics.tests.factories import BusinessAreaFactory
from vision.adapters.publics_adapter import CostAssignmentsSyncronizer


class AdapterTest(APITenantTestCase):

    def setUp(self):
        super(AdapterTest, self).setUp()
        # This code belongs to Sri Lanka
        self.business_area_code = '0780'
        self.business_area = BusinessAreaFactory(code=self.business_area_code)

    @VCR.use_cassette('cost_assignment_adapter.yaml')
    def test_cost_assignment_adapter(self):

        workspace = connection.tenant
        workspace.business_area_code = self.business_area.code

        syncer = CostAssignmentsSyncronizer(workspace)

        wbs_qs = WBS.objects.all()
        grant_qs = Grant.objects.all()
        fund_qs = Fund.objects.all()

        self.assertEqual(wbs_qs.count(), 0)
        self.assertEqual(grant_qs.count(), 0)
        self.assertEqual(fund_qs.count(), 0)

        with self.assertNumQueries(686):
            syncer.sync()

        self.assertEqual(wbs_qs.count(), 101)
        self.assertEqual(grant_qs.count(), 124)
        self.assertEqual(fund_qs.count(), 9)
