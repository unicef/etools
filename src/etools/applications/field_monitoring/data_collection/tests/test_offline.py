from unittest.mock import patch

from django.core.management import call_command
from django.db import connection
from django.test import override_settings

import simplejson
from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.environment.models import TenantSwitch
from etools.applications.environment.tests.factories import TenantSwitchFactory
from etools.applications.field_monitoring.data_collection.models import StartedChecklist
from etools.applications.field_monitoring.data_collection.tests.factories import (
    ActivityQuestionFactory,
    StartedChecklistFactory,
)
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import MethodFactory
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.tpm.tests.factories import TPMPartnerFactory, TPMPartnerStaffMemberFactory


class ChecklistBlueprintViewTestCase(APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_data_collection:checklists'

    @classmethod
    def setUpTestData(cls):
        cls.team_member = UserFactory(unicef_user=True)
        cls.visit_lead = UserFactory(unicef_user=True)

        partner = PartnerFactory()
        cls.activity = MonitoringActivityFactory(
            status='data_collection',
            visit_lead=cls.visit_lead,
            team_members=[cls.team_member],
            partners=[partner],
        )
        cls.text_question = ActivityQuestionFactory(
            question__answer_type=Question.ANSWER_TYPES.text,
            monitoring_activity=cls.activity, partner=partner,
            question__methods=[MethodFactory(use_information_source=True)]
        )
        cls.started_checklist = StartedChecklistFactory(
            monitoring_activity=cls.activity,
            method=cls.text_question.question.methods.first(),
            author=cls.team_member
        )

    def get_list_args(self):
        return [self.activity.id]

    def test_get_blueprint(self):
        AttachmentFactory(content_object=self.started_checklist.overall_findings.first(), code='attachments')
        with self.assertNumQueries(16):  # todo: optimize queries
            response = self.make_detail_request(self.team_member, self.started_checklist, action='blueprint',
                                                method='get')
        data = response.data
        self.assertIn('blueprint', data)
        self.assertIn('structure', data['blueprint'])
        self.assertIn('children', data['blueprint']['structure'])

        root_fields = data['blueprint']['structure']['children']
        self.assertEqual('information_source', root_fields[0]['name'])
        self.assertEqual('partner', root_fields[1]['name'])
        self.assertEqual(str(self.text_question.partner.id), root_fields[1]['children'][0]['name'])

        partner_fields = root_fields[1]['children'][0]['children']
        self.assertEqual('overall', partner_fields[0]['name'])
        self.assertEqual('attachments', partner_fields[1]['name'])
        self.assertEqual('questions', partner_fields[2]['name'])

    def test_save_blueprint_values(self):
        partner = self.text_question.partner
        attachments = AttachmentFactory.create_batch(size=2)
        file_type = AttachmentFileTypeFactory(code='fm_common')
        # with self.assertNumQueries(38):  # todo: optimize
        response = self.make_detail_request(
            self.team_member, self.started_checklist, action='blueprint', method='post',
            data={
                'information_source': {
                    'name': 'Doctors',
                },
                'partner': {
                    str(partner.id): {
                        'overall': 'overall',
                        'attachments': [
                            {'attachment': a.id, 'file_type': file_type.id}
                            for a in attachments
                        ],
                        'questions': {
                            str(self.text_question.question_id): 'Question answer'
                        }
                    }
                }
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_save_long_information_source(self):
        response = self.make_detail_request(
            self.team_member, self.started_checklist, action='blueprint', method='post',
            data={
                'information_source': {
                    'name': '0' * 101,
                },
                'partner': {
                    str(self.text_question.partner.id): {
                        'overall': 'overall',
                        'questions': {
                            str(self.text_question.question_id): 'Question answer'
                        }
                    }
                }
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('information_source', response.data)

    def test_generated_blueprint_value_accepted_for_saving(self):
        AttachmentFactory(
            content_object=self.started_checklist.overall_findings.first(),
            file_type=AttachmentFileTypeFactory(code='fm_common'),
            code='attachments'
        )

        blueprint_response = self.make_detail_request(
            self.team_member, self.started_checklist, action='blueprint'
        )

        response = self.make_detail_request(
            self.team_member, self.started_checklist, action='blueprint', method='post',
            data=blueprint_response.data['value']
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_save_blueprint_values_error(self):
        response = self.make_detail_request(
            self.team_member, self.started_checklist, action='blueprint', method='post',
            data={'test': 'value'}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual(response.data, {'information_source': ['This field is required']})

    def test_save_blueprint_values_validation(self):
        response = self.make_detail_request(
            self.team_member,
            self.started_checklist,
            action='blueprint',
            method='post',
            data={'information_source': {'name': 'value' * 100}}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            {'name': ['Ensure this field has no more than 100 characters.']},
            response.data['information_source'],
        )


class MonitoringActivityOfflineBlueprintsSyncTestCase(APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:activities'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.fm_user = UserFactory(first_name='Field Monitoring User', fm_user=True, is_staff=True)

    def setUp(self):
        super().setUp()
        call_command("update_notifications")
        TenantSwitch.get("fm_offline_sync_disabled").flush()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_blueprints_sent_on_tpm_data_collection(self, add_mock):
        tpm_partner = TPMPartnerFactory()
        visit_lead = TPMPartnerStaffMemberFactory(tpm_partner=tpm_partner).user
        activity = MonitoringActivityFactory(
            status='assigned', partners=[PartnerFactory()], monitor_type='tpm', tpm_partner=tpm_partner,
            visit_lead=visit_lead, team_members=[visit_lead]
        )
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(
            activity.visit_lead, activity,
            {'status': 'data_collection'}
        )
        add_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_blueprints_sent_on_staff_assignment(self, add_mock):
        activity = MonitoringActivityFactory(status='pre_assigned', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'assigned'})
        add_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_tenant_switch_missing(self, add_mock):
        activity = MonitoringActivityFactory(status='pre_assigned', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'assigned'})
        add_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_tenant_switch_enabled(self, add_mock):
        TenantSwitchFactory(name="fm_offline_sync_disabled", countries=[connection.tenant], active=True)
        activity = MonitoringActivityFactory(status='pre_assigned', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'assigned'})
        add_mock.assert_not_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_tenant_switch_disabled(self, add_mock):
        TenantSwitchFactory(name="fm_offline_sync_disabled", countries=[connection.tenant], active=False)
        activity = MonitoringActivityFactory(status='pre_assigned', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'assigned'})
        add_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.update')
    def test_blueprint_updated_on_visit_lead_change(self, update_mock):
        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        update_mock.reset_mock()
        activity.visit_lead = UserFactory()
        activity.save()
        update_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.update')
    def test_blueprint_updated_on_team_member_add(self, update_mock):
        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        update_mock.reset_mock()
        activity.team_members.add(UserFactory())
        update_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.update')
    def test_blueprint_updated_on_team_member_remove(self, update_mock):
        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        update_mock.reset_mock()
        activity.team_members.remove(activity.team_members.first())
        update_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.delete')
    def test_blueprints_deleted_on_activity_cancel(self, delete_mock):
        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        delete_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'cancelled', 'cancel_reason': 'For testing purposes'})
        delete_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.delete')
    def test_blueprints_deleted_on_activity_report_finalization(self, delete_mock):
        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        method = MethodFactory()
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[method])
        StartedChecklistFactory(monitoring_activity=activity, method=method)

        delete_mock.reset_mock()
        self._test_update(activity.visit_lead, activity, {'status': 'report_finalization'})
        delete_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_tenant_switch_missing_but_api_not_configured(self, add_mock):
        activity = MonitoringActivityFactory(status='pre_assigned', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'assigned'})
        add_mock.assert_not_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/', SENTRY_DSN='https://test.dns')
    @patch('sentry_sdk.api.Hub.current.capture_exception')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_add_offline_backend_unavailable(self, add_mock, capture_event_mock):
        def communication_failure(*args, **kwargs):
            return 502, simplejson.loads(
                '<html>\r\n<head><title>502 Bad Gateway</title></head>\r\n<body bgcolor="white">\r\n<center>'
                '<h1>502 Bad Gateway</h1></center>\r\n<hr><center>nginx/1.13.12</center>\r\n</body>\r\n</html>\r\n'
            )

        add_mock.side_effect = communication_failure

        activity = MonitoringActivityFactory(status='pre_assigned', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        self._test_update(self.fm_user, activity, {'status': 'assigned'})
        capture_event_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/', SENTRY_DSN='https://test.dns')
    @patch('sentry_sdk.api.Hub.current.capture_exception')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.update')
    def test_update_offline_backend_unavailable(self, update_mock, capture_event_mock):
        def communication_failure(*args, **kwargs):
            return 502, simplejson.loads(
                '<html>\r\n<head><title>502 Bad Gateway</title></head>\r\n<body bgcolor="white">\r\n<center>'
                '<h1>502 Bad Gateway</h1></center>\r\n<hr><center>nginx/1.13.12</center>\r\n</body>\r\n</html>\r\n'
            )

        update_mock.side_effect = communication_failure

        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        activity.team_members.remove(activity.team_members.first())
        capture_event_mock.assert_called()

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/', SENTRY_DSN='https://test.dns')
    @patch('sentry_sdk.api.Hub.current.capture_exception')
    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.delete')
    def test_delete_offline_backend_unavailable(self, delete_mock, capture_event_mock):
        def communication_failure(*args, **kwargs):
            return 502, simplejson.loads(
                '<html>\r\n<head><title>502 Bad Gateway</title></head>\r\n<body bgcolor="white">\r\n<center>'
                '<h1>502 Bad Gateway</h1></center>\r\n<hr><center>nginx/1.13.12</center>\r\n</body>\r\n</html>\r\n'
            )

        delete_mock.side_effect = communication_failure

        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        self._test_update(self.fm_user, activity, {'status': 'cancelled', 'cancel_reason': 'For testing purposes'})
        capture_event_mock.assert_called()


class MonitoringActivityOfflineValuesTestCase(APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_data_collection:activities'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = None
        cls.partner = PartnerFactory()
        cls.activity = MonitoringActivityFactory(status='data_collection', partners=[cls.partner])
        cls.method = MethodFactory(use_information_source=True)
        cls.activity_question = ActivityQuestionFactory(
            monitoring_activity=cls.activity, is_enabled=True, partner=cls.partner,
            question__methods=[cls.method], question__answer_type='text'
        )

        cls.user = cls.activity.visit_lead

    def get_detail_args(self, instance):
        return [instance.pk, self.method.pk]

    @override_settings(ETOOLS_OFFLINE_API='http://example.com/b/api/remote/blueprint/')
    @patch('etools.applications.offline.fields.files.download_remote_attachment.delay')
    def test_checklist_saving(self, download_mock):
        file_type = AttachmentFileTypeFactory(code='fm_common').id
        schema_name = connection.tenant.schema_name

        connection.set_schema_to_public()

        response = self.make_detail_request(
            None, self.activity, method='post', action='offline',
            QUERY_STRING='user={}&workspace={}'.format(self.user.email, schema_name),
            data={
                'information_source': {'name': 'Doctors'},
                'partner': {
                    self.partner.id: {
                        'overall': 'overall',
                        'attachments': [
                            {
                                'attachment': 'http://example.com',
                                'file_type': file_type
                            }
                        ],
                        'questions': {
                            str(self.activity_question.question_id): 'Question answer'
                        }
                    }
                }
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        checklist = StartedChecklist.objects.filter(
            author=self.user, monitoring_activity=self.activity, method=self.method
        ).first()
        self.assertTrue(bool(checklist))

        # check attachment mapped
        attachment = checklist.overall_findings.first().attachments.first()
        self.assertTrue(bool(attachment))
        self.assertEqual(attachment.uploaded_by, self.user)

        # check correct url called
        download_mock.assert_called()
        self.assertIn(attachment.id, download_mock.call_args_list[0][0])
        self.assertIn('http://example.com', download_mock.call_args_list[0][0])

    def test_checklist_form_error(self):
        response = self.make_detail_request(
            None, self.activity, method='post', action='offline',
            QUERY_STRING='user={}&workspace={}'.format(self.user.email, connection.tenant.schema_name),
            data={'information_source': {}}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.data,
            {
                'information_source': {'name': ['This field is required']},
            }
        )

    def test_transaction(self):
        response = self.make_detail_request(
            None, self.activity, method='post', action='offline',
            QUERY_STRING='user={}&workspace={}'.format(self.user.email, connection.tenant.schema_name),
            data={'information_source': {'name': 'test'}, 'partner': {'-1': {}}}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(
            StartedChecklist.objects.filter(
                author=self.user, monitoring_activity=self.activity, method=self.method
            ).exists()
        )

    def test_workspace_required(self):
        response = self.make_detail_request(
            None, self.activity, method='post', action='offline',
            QUERY_STRING='user={}'.format(self.user.email),
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_user_required(self):
        response = self.make_detail_request(
            None, self.activity, method='post', action='offline',
            QUERY_STRING='workspace={}'.format(connection.tenant.schema_name),
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_offline_locked_for_report_finalization_status(self):
        partner = PartnerFactory()
        activity = MonitoringActivityFactory(status='report_finalization', partners=[partner])
        ActivityQuestionFactory(
            monitoring_activity=activity, is_enabled=True, partner=partner,
            question__methods=[self.method], question__answer_type='text'
        )
        response = self.make_detail_request(
            None, activity, method='post', action='offline',
            QUERY_STRING='user={}&workspace={}'.format(self.user.email, connection.tenant.schema_name),
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
