from __future__ import unicode_literals

from django.db import connection
from django.test.utils import override_settings

from EquiTrack.tests.mixins import APITenantTestCase, VCR
from publics.models import WBS, Grant, Fund, WBSGrantThrough, GrantFundThrough
from publics.tests.factories import BusinessAreaFactory
from vision.adapters.publics_adapter import CostAssignmentsSyncronizer


class AdapterTest(APITenantTestCase):
    maxDiff = None

    def setUp(self):
        super(AdapterTest, self).setUp()
        # This code belongs to Sri Lanka
        self.business_area_code = '0780'
        self.business_area = BusinessAreaFactory(code=self.business_area_code)

    # If the casette has to be rerecorded, this url has to be set to the proper one
    @override_settings(VISION_URL='https://fake.vision.url/BIService/BIWebService.svc')
    @VCR.use_cassette('cost_assignment_adapter.yaml', match_on=['path', 'method'])
    def test_cost_assignment_adapter(self):

        workspace = connection.tenant
        workspace.business_area_code = self.business_area.code

        syncer = CostAssignmentsSyncronizer(workspace)

        wbs_qs = WBS.objects.all()
        grant_qs = Grant.objects.all()
        fund_qs = Fund.objects.all()

        wbs_grant_qs = WBSGrantThrough.objects.all()
        grant_fund_qs = GrantFundThrough.objects.all()

        self.assertEqual(wbs_qs.count(), 0)
        self.assertEqual(grant_qs.count(), 0)
        self.assertEqual(fund_qs.count(), 0)

        self.assertEqual(wbs_grant_qs.count(), 0)
        self.assertEqual(grant_fund_qs.count(), 0)

        with self.assertNumQueries(13):
            syncer.sync()

        self.assertEqual(wbs_qs.count(), 101)
        self.assertEqual(grant_qs.count(), 124)
        self.assertEqual(fund_qs.count(), 9)

        self.assertEqual(wbs_grant_qs.count(), 832)
        self.assertEqual(grant_fund_qs.count(), 124)
