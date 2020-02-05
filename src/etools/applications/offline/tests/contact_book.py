from etools.applications.offline.blueprint import Blueprint
from etools.applications.offline.fields import ChoiceField, Group, TextField
from etools.applications.offline.fields.choices import LocalFlatOptions
from etools.applications.offline.validations.text import RegexTextValidation

contact_book = Blueprint('example_contact_book', 'Contact Book example')
contact_book.add(
    TextField('name', label='Name', required=True),
    Group(
        'users',
        TextField('full_name', required=True),
        Group(
            'phones',
            TextField('number', required=True, validations=['phone_regex']),
            TextField('type', required=False),
            required=True, repeatable=True, title='Phones',
        ),
        ChoiceField('groups', required=False, repeatable=True, options_key='groups'),
        required=False, repeatable=True, title='Users',
    ),
)
contact_book.metadata.options['groups'] = LocalFlatOptions(['family', 'friends', 'work', 'other'])
contact_book.metadata.validations['phone_regex'] = RegexTextValidation(r'\d{7}')
