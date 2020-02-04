from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
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
        with self.assertNumQueries(17):  # todo: optimize queries
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
                'information_source': 'Doctors',
                'partner': {
                    str(partner.id): {
                        'overall': 'overall',
                        'attachments': [
                            {'attachment': a.id, 'file_type': file_type.id}
                            for a in attachments
                        ],
                        'questions': {
                            str(self.text_question.id): 'Question answer'
                        }
                    }
                }
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
