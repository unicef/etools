import json

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.offline.blueprint import get_monitoring_activity_blueprints
from etools.applications.field_monitoring.data_collection.offline.helpers import create_checklist
from etools.applications.field_monitoring.data_collection.tests.factories import ActivityQuestionFactory
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import MethodFactory
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import PartnerFactory


class OfflineStructureTestCase(BaseTenantTestCase):
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
        cls.likert_question = ActivityQuestionFactory(
            question__answer_type=Question.ANSWER_TYPES.likert_scale,
            monitoring_activity=cls.activity, partner=partner,
            question__methods=[MethodFactory()]
        )
        cls.text_question = ActivityQuestionFactory(
            question__answer_type=Question.ANSWER_TYPES.text,
            monitoring_activity=cls.activity, partner=partner,
            question__methods=[MethodFactory()]
        )

    def test_structure_json(self):
        print(json.dumps([bp.to_dict() for bp in get_monitoring_activity_blueprints(self.activity)], indent=2))

    def test_save_checklist(self):
        partner = self.text_question.partner
        create_checklist(self.activity, self.text_question.question.methods.first(), UserFactory(), {
            'information_source': 'Doctors',
            'partner': {
                str(partner.id): {
                    'overall': 'overall',
                    'attachments': [
                        {'attachment': a.id, 'file_type': a.file_type.id}
                        for a in AttachmentFactory.create_batch(size=2, file_type__code='fm_common')
                    ],
                    'questions': {
                        str(self.text_question.id): 'Question answer'
                    }
                }
            }
        })
