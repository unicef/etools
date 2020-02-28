from django.db import connection
from mock import patch
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
        cls.person_responsible = UserFactory(unicef_user=True)

        partner = PartnerFactory()
        cls.activity = MonitoringActivityFactory(
            status='data_collection',
            person_responsible=cls.person_responsible,
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
            data={'information_source': {'name': 'Doctors'}}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual(response.data, {'partner': ['This field is required']})


class MonitoringActivityOfflineBlueprintsSyncTestCase(APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:activities'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.fm_user = UserFactory(first_name='Field Monitoring User', fm_user=True, is_staff=True,
                                  profile__countries_available=[connection.tenant])

    def setUp(self):
        super().setUp()
        TenantSwitch.get("fm_offline_sync_disabled").flush()

    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_blueprints_sent_on_tpm_data_collection(self, add_mock):
        tpm_partner = TPMPartnerFactory()
        person_responsible = TPMPartnerStaffMemberFactory(tpm_partner=tpm_partner).user
        activity = MonitoringActivityFactory(
            status='assigned', partners=[PartnerFactory()], monitor_type='tpm', tpm_partner=tpm_partner,
            person_responsible=person_responsible, team_members=[person_responsible]
        )
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(
            activity.person_responsible, activity,
            {'status': 'data_collection'}
        )
        add_mock.assert_called()

    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_blueprints_sent_on_staff_assignment(self, add_mock):
        activity = MonitoringActivityFactory(status='pre_assigned', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'assigned'})
        add_mock.assert_called()

    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_tenant_switch_missing(self, add_mock):
        activity = MonitoringActivityFactory(status='pre_assigned', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'assigned'})
        add_mock.assert_called()

    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_tenant_switch_enabled(self, add_mock):
        TenantSwitchFactory(name="fm_offline_sync_disabled", countries=[connection.tenant], active=True)
        activity = MonitoringActivityFactory(status='pre_assigned', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'assigned'})
        add_mock.assert_not_called()

    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.add')
    def test_tenant_switch_disabled(self, add_mock):
        TenantSwitchFactory(name="fm_offline_sync_disabled", countries=[connection.tenant], active=False)
        activity = MonitoringActivityFactory(status='pre_assigned', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        add_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'assigned'})
        add_mock.assert_called()

    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.update')
    def test_blueprint_updated_on_person_responsible_change(self, update_mock):
        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        update_mock.reset_mock()
        activity.person_responsible = UserFactory()
        activity.save()
        update_mock.assert_called()

    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.update')
    def test_blueprint_updated_on_team_member_add(self, update_mock):
        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        update_mock.reset_mock()
        activity.team_members.add(UserFactory())
        update_mock.assert_called()

    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.update')
    def test_blueprint_updated_on_team_member_remove(self, update_mock):
        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        update_mock.reset_mock()
        activity.team_members.remove(activity.team_members.first())
        update_mock.assert_called()

    @patch('etools.applications.field_monitoring.data_collection.offline.synchronizer.OfflineCollect.delete')
    def test_blueprints_deleted_on_activity_cancel(self, delete_mock):
        activity = MonitoringActivityFactory(status='data_collection', partners=[PartnerFactory()])
        ActivityQuestionFactory(monitoring_activity=activity, is_enabled=True, question__methods=[MethodFactory()])

        delete_mock.reset_mock()
        self._test_update(self.fm_user, activity, {'status': 'cancelled', 'cancel_reason': 'For testing purposes'})
        delete_mock.assert_called()


class MonitoringActivityOfflineValuesTestCase(APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_data_collection:activities'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.fm_user = UserFactory(first_name='Field Monitoring User', fm_user=True, is_staff=True,
                                  profile__countries_available=[connection.tenant])

        cls.user = None
        cls.partner = PartnerFactory()
        cls.activity = MonitoringActivityFactory(status='data_collection', partners=[cls.partner])
        cls.method = MethodFactory(use_information_source=True)
        cls.activity_question = ActivityQuestionFactory(
            monitoring_activity=cls.activity, is_enabled=True, partner=cls.partner,
            question__methods=[cls.method], question__answer_type='text'
        )

    def get_detail_args(self, instance):
        return [instance.pk, self.method.pk]

    @patch('etools.applications.offline.fields.files.download_remote_attachment.delay')
    def test_checklist_saving(self, download_mock):
        response = self.make_detail_request(
            None, self.activity, method='post', action='offline',
            QUERY_STRING='user={}'.format(self.fm_user.email),
            data={
                'information_source': {'name': 'Doctors'},
                'partner': {
                    str(self.partner.id): {
                        'overall': 'overall',
                        'attachments': [
                            {
                                'attachment': 'http://example.com',
                                'file_type': AttachmentFileTypeFactory(code='fm_common').id
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
        self.assertTrue(
            StartedChecklist.objects.filter(
                author=self.fm_user, monitoring_activity=self.activity, method=self.method
            ).exists()
        )
        download_mock.assert_called()
        self.assertIn('http://example.com', download_mock.call_args_list[0][0])

    def test_checklist_form_error(self):
        response = self.make_detail_request(
            None, self.activity, method='post', action='offline',
            QUERY_STRING='user={}'.format(self.fm_user.email),
            data={'information_source': {}, 'partner': {}}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.data,
            {
                'information_source': {'name': ['This field is required']},
                'partner': {str(self.partner.pk): ['This field is required']}
            }
        )
