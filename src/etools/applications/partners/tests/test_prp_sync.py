from collections import namedtuple

from django.db import connection
from django.utils import timezone

from mock import patch

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tasks import sync_partner_to_prp
from etools.applications.partners.tests.factories import InterventionFactory


class TestInterventionPartnerSyncSignal(BaseTenantTestCase):
    @patch('etools.applications.partners.signals.sync_partner_to_prp.delay')
    def test_intervention_sync_called(self, sync_task_mock):
        intervention = InterventionFactory()
        sync_task_mock.assert_not_called()

        intervention.date_sent_to_partner = timezone.now()
        intervention.save()
        sync_task_mock.assert_called_with(connection.tenant.name, intervention.agreement.partner_id)

    @patch('etools.applications.partners.signals.sync_partner_to_prp.delay')
    def test_intervention_sync_not_called_on_save(self, sync_task_mock):
        intervention = InterventionFactory()
        sync_task_mock.assert_not_called()

        intervention.start = timezone.now()
        intervention.save()
        sync_task_mock.assert_not_called()

    @patch('etools.applications.partners.signals.sync_partner_to_prp.delay')
    def test_intervention_sync_called_on_create(self, sync_task_mock):
        intervention = InterventionFactory(date_sent_to_partner=timezone.now())
        sync_task_mock.assert_called_with(connection.tenant.name, intervention.agreement.partner_id)


class TestInterventionPartnerSyncTask(BaseTenantTestCase):
    @patch(
        'etools.applications.partners.prp_api.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text'])(200, '{}')
    )
    def test_request_to_prp_sent(self, request_mock):
        intervention = InterventionFactory()
        request_mock.assert_not_called()

        sync_partner_to_prp(connection.tenant.name, intervention.agreement.partner_id)
        request_mock.assert_called()
