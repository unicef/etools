import json

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.offline.blueprint import get_monitoring_activity_blueprints
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
        print(json.dumps({
            key: bp.to_dict()
            for key, bp in get_monitoring_activity_blueprints(self.activity).items()
        }, indent=2))
