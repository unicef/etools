import json

from django.test import TestCase

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.offline.blueprint.base import Blueprint
from etools.applications.field_monitoring.data_collection.offline.errors import ValidationError
from etools.applications.field_monitoring.data_collection.offline.fm_utils import get_monitoring_activity_blueprints
from etools.applications.field_monitoring.data_collection.offline.structure.base import Field, Group
from etools.applications.field_monitoring.data_collection.offline.validations.text import RegexTextValidation
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


class ContactBookExampleTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.contact_book = Blueprint('example_contact_book', 'Contact Book example')
        cls.contact_book.add(
            Field('name', 'text', label='Name', required=True),
            Group(
                'users',
                Field('full_name', 'text', required=True),
                Group(
                    'phones',
                    Field('number', 'text', required=True, validations=['phone_regex']),
                    Field('type', 'text', required=False),
                    required=True, repeatable=True, title='Phones',
                ),
                Field('groups', 'dropdown', required=False, repeatable=True, options_key='groups'),
                required=False, repeatable=True, title='Users',
            ),
        )
        cls.contact_book.metadata.options['groups'] = {
            'options_type': 'local_flat',
            'values': ['family', 'friends', 'work', 'other']
        }
        cls.contact_book.metadata.validations['phone_regex'] = RegexTextValidation(r'\d{7}')

    def test_structure_json(self):
        print(json.dumps(self.contact_book.to_dict(), indent=2))

    def test_form_validation(self):
        self.contact_book.validate({
            'name': 'test book',
            'users': [
                {
                    'full_name': 'John Doe',
                    'phones': [
                        {'number': '1234567', 'type': 'mobile'},
                        {'number': '2222222', 'type': 'work'},
                        {'number': '2222242'},
                    ],
                    'groups': ['test']  # todo: how resolve options? metadata? if remote choices? hidden validator?
                },
            ]
        })

    def test_users_not_required(self):
        self.contact_book.validate({'name': 'test'})

    def test_phones_required(self):
        value = {'name': 'test', 'users': [{'full_name': 'John Doe'}]}
        with self.assertRaises(ValidationError):
            self.contact_book.validate(value)
        value['users'][0]['phones'] = [{'number': '1234567'}]
        self.contact_book.validate(value)

    def test_name_required(self):
        value = {}
        with self.assertRaises(ValidationError):
            self.contact_book.validate(value)
        value['name'] = 'test'
        self.contact_book.validate(value)

    def test_number_regex(self):
        value = {'name': 'test', 'users': [{'full_name': 'John Doe', 'phones': [{'number': '123456'}]}]}
        with self.assertRaises(ValidationError):
            self.contact_book.validate(value)
        value['users'][0]['phones'][0]['number'] = '1234567'
        self.contact_book.validate(value)
