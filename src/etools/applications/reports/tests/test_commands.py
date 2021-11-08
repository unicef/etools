
from django.core.management import call_command

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import InterventionResultLinkFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import (
    InterventionActivityFactory,
    InterventionActivityItemFactory,
    LowerResultFactory,
)


class TestResultTypeCommand(BaseTenantTestCase):

    def test_command(self):
        self.assertEqual(ResultType.objects.count(), 0)
        call_command('init-result-type')
        self.assertEqual(ResultType.objects.count(), 3)


class TestFixActivityTotalsCommand(BaseTenantTestCase):
    def test_command(self):
        lower_result = LowerResultFactory(result_link=InterventionResultLinkFactory())
        # bad activity
        activity = InterventionActivityFactory(result=lower_result)
        InterventionActivityItemFactory(activity=activity, unicef_cash=4, cso_cash=5)
        activity.cso_cash = 0
        activity.unicef_cash = 0
        activity.save()

        # regular activity without items
        activity1 = InterventionActivityFactory(result=lower_result, cso_cash=6, unicef_cash=7)

        call_command('fix-activity-totals')
        activity.refresh_from_db()
        activity1.refresh_from_db()

        # activity cash recalculated
        self.assertEqual(activity.unicef_cash, 4)
        self.assertEqual(activity.cso_cash, 5)

        # values untouched
        self.assertEqual(activity1.cso_cash, 6)
        self.assertEqual(activity1.unicef_cash, 7)
