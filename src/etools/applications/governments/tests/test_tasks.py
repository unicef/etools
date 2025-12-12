import datetime
import json
from collections import namedtuple
from unittest import mock

from django.db import connection
from django.test import override_settings

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory, FundsReservationItemFactory
from etools.applications.governments.models import GDD
from etools.applications.governments.serializers.exports.vision.gdd_v1 import GDDVisionExportSerializer
from etools.applications.governments.tasks import GDDVisionUploader, send_gdd_to_vision
from etools.applications.governments.tests.factories import (
    EWPActivityFactory,
    EWPOutputFactory,
    GDDActivityFactory,
    GDDFactory,
    GDDKeyInterventionFactory,
    GDDResultLinkFactory,
)
from etools.applications.reports.models import ResultType
from etools.applications.vision.models import VisionSyncLog


@mock.patch('etools.applications.governments.tasks.logger', spec=['info', 'warning', 'error', 'exception'])
@override_settings(
    EZHACT_PD_VISION_URL='https://example.com/upload/gpd/',
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
)
class SendGPDToVisionTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.draft_gpd = GDDFactory()
        cls.active_gpd = GDDFactory(
            status=GDD.ACTIVE,
            date_sent_to_partner=datetime.date.today()
        )
        frs = FundsReservationHeaderFactory(
            gdd=cls.active_gpd,
            currency='USD',
        )
        FundsReservationItemFactory(fund_reservation=frs)
        cls.result = EWPOutputFactory(
            cp_output__result_type__name=ResultType.OUTPUT,
        )
        cls.link = GDDResultLinkFactory(
            cp_output=cls.result,
            gdd=cls.active_gpd,
            workplan=cls.result.workplan
        )
        cls.key_intervention = GDDKeyInterventionFactory(result_link=cls.link)
        cls.activity = GDDActivityFactory(key_intervention=cls.key_intervention, unicef_cash=10, ewp_activity=EWPActivityFactory())

    def test_sync_validation_error(self, logger_mock):
        send_gdd_to_vision(connection.tenant.name, self.draft_gpd.pk)
        logger_mock.info.assert_called_with('Instance is not ready to be synchronized')

    @mock.patch(
        'etools.applications.partners.synchronizers.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text', 'json'])(502, '', lambda: None)
    )
    def test_sync_bad_response(self, _requests_mock, logger_mock):
        send_gdd_to_vision(connection.tenant.name, self.active_gpd.pk)
        self.assertTrue(mock.call('Received 502 from vision synchronizer. retrying') in logger_mock.info.mock_calls)
        self.assertTrue(
            mock.call(
                f'Received 502 from vision synchronizer after 3 attempts. '
                f'GPD id: {self.active_gpd.pk}. Business area code: {connection.tenant.business_area_code}'
            ) in logger_mock.exception.mock_calls
        )
        vision_log = VisionSyncLog.objects.filter(
            country=connection.tenant,
            handler_name='GDDVisionUploader'
        ).last()
        self.assertTrue(vision_log.data, GDDVisionExportSerializer(self.active_gpd).data)

    @mock.patch(
        'etools.applications.partners.synchronizers.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text', 'json'])(200, '{}', lambda: {})
    )
    def test_sync_success(self, _requests_mock, logger_mock):
        send_gdd_to_vision(connection.tenant.name, self.active_gpd.pk)
        self.assertTrue(mock.call('Completed gpd synchronization') in logger_mock.info.mock_calls)
        vision_log = VisionSyncLog.objects.filter(
            country=connection.tenant,
            handler_name='GDDVisionUploader'
        ).last()
        self.assertTrue(vision_log.data, GDDVisionExportSerializer(self.active_gpd).data)

    @mock.patch('etools.applications.partners.synchronizers.requests.post',
                return_value=namedtuple('Response', ['status_code', 'text', 'json'])(200, '', lambda: None))
    def test_business_code_in_data(self, requests_mock, _logger_mock):
        send_gdd_to_vision(connection.tenant.name, self.active_gpd.pk)
        self.assertIn('business_area', json.loads(requests_mock.mock_calls[0][2]['data']))

    def test_body_rendering(self, _logger_mock):
        synchronizer = GDDVisionUploader(GDD.objects.detail_qs().get(pk=self.active_gpd.pk))
        str_data = synchronizer.render()
        self.assertIsInstance(str_data, bytes)
        self.assertGreater(len(str_data), 100)

    @mock.patch(
        'etools.applications.partners.synchronizers.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text', 'json'])(200, '{}', lambda: {})
    )
    def test_payload_sent_to_vision_contain_code_prefix(self, requests_mock, _logger_mock):
        send_gdd_to_vision(connection.tenant.name, self.active_gpd.pk)

        sent_body = requests_mock.mock_calls[0][2]['data']
        payload = json.loads(sent_body)
        result_links = payload.get('result_links', [])
        gdd_key_interventions = result_links[0].get('gdd_key_interventions', [])
        activities = gdd_key_interventions[0].get('activities', [])

        first_result = gdd_key_interventions[0]

        self.assertEqual(
            first_result.get('name'),
            self.key_intervention.ewp_key_intervention.cp_key_intervention.name,
        )

        matched = {a.get('id'): a for a in activities}.get(self.activity.id)
        self.assertIsNotNone(matched, 'Created activity must be present in payload')
        self.assertTrue(matched['name'], self.activity.name)
