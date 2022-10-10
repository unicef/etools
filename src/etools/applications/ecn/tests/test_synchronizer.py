from decimal import Decimal
from unittest.mock import patch

from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.ecn.synchronizer import ECNSynchronizer
from etools.applications.ecn.tests.utils import get_example_ecn
from etools.applications.partners.tests.factories import AgreementFactory
from etools.applications.reports.tests.factories import OfficeFactory, SectionFactory
from etools.applications.users.tests.factories import UserFactory


class TestSynchronizer(BaseTenantTestCase):
    @patch('etools.applications.ecn.api.ECNAPI.get_intervention')
    def test_sync(self, request_intervention_mock):
        request_intervention_mock.return_value = get_example_ecn()

        agreement = AgreementFactory()
        sections = [SectionFactory()]
        locations = [LocationFactory() for _li in range(5)]
        offices = [OfficeFactory() for _oi in range(4)]
        intervention = ECNSynchronizer(UserFactory()).synchronize(1, agreement, sections, locations, offices)

        self.assertEqual(intervention.risks.count(), 1)
        self.assertEqual(intervention.supply_items.count(), 2)
        self.assertEqual(intervention.result_links.count(), 1)
        result_link = intervention.result_links.first()
        self.assertEqual(result_link.ll_results.count(), 2)
        lower_result = result_link.ll_results.get(name='pd output 1')
        self.assertEqual(lower_result.activities.count(), 2)
        activity = lower_result.activities.get(name='activity 1')
        self.assertListEqual(list(activity.time_frames.values_list('quarter', flat=True)), [2])
        self.assertEqual(activity.items.count(), 1)
        self.assertTrue(lower_result.applied_indicators.filter(indicator__title='test indicator 1').exists())
        self.assertEqual(intervention.planned_budget.partner_contribution_local, Decimal("16615.00"))
        self.assertEqual(intervention.flat_locations.count(), 5)
        self.assertEqual(intervention.offices.count(), 4)
