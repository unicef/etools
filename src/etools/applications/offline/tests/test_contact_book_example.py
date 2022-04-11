import json
import os

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.offline.errors import ValidationError
from etools.applications.offline.tests.contact_book import contact_book


class ContactBookExampleTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

    def test_serialized_structure(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'contact_book.json'), 'r') as example:
            self.maxDiff = None
            self.assertDictEqual(json.load(example), contact_book.to_dict())

    def test_form_validation(self):
        contact_book.validate({
            'name': 'test book',
            'users': [
                {
                    'full_name': 'John Doe',
                    'phones': [
                        {'number': 1234567, 'type': 'mobile'},
                        {'number': '2222222', 'type': 'work'},
                        {'number': '2222242'},
                    ],
                    'groups': ['friends']
                },
            ]
        })

    def test_users_not_required(self):
        contact_book.validate({'name': 'test'})

    def test_phones_required(self):
        value = {'name': 'test', 'users': [{'full_name': 'John Doe'}]}
        with self.assertRaises(ValidationError) as err:
            contact_book.validate(value)
        self.assertDictEqual({'users': [{'phones': ['This field is required']}]}, err.exception.detail)

        value['users'][0]['phones'] = [{'number': '1234567'}]
        contact_book.validate(value)

    def test_name_required(self):
        value = {'name': None}
        with self.assertRaises(ValidationError) as err:
            contact_book.validate(value)
        self.assertDictEqual({'name': ['This field is required']}, err.exception.detail)

        value['name'] = 'test'
        contact_book.validate(value)

    def test_number_regex(self):
        value = {'name': 'test', 'users': [{'full_name': 'John Doe', 'phones': [{'number': '123456'}]}]}
        with self.assertRaises(ValidationError) as err:
            contact_book.validate(value)
        self.assertDictEqual({'users': [{'phones': [{'number': ['Invalid value: 123456']}]}]}, err.exception.detail)

        value['users'][0]['phones'][0]['number'] = '1234567'
        contact_book.validate(value)

    def test_invalid_group_choice(self):
        value = {
            'name': 'test',
            'users': [{'full_name': 'John Doe', 'phones': [{'number': '1234567'}], 'groups': ['test']}]
        }

        with self.assertRaises(ValidationError) as err:
            contact_book.validate(value)
        self.assertDictEqual({'users': [{'groups': [['Invalid value: test']]}]}, err.exception.detail)

        value['users'][0]['groups'] = ['work']
        contact_book.validate(value)
