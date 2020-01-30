from etools.applications.offline.blueprint import Blueprint
from etools.applications.offline.structure import Field, Group
from etools.applications.offline.validations.text import RegexTextValidation

contact_book = Blueprint('example_contact_book', 'Contact Book example')
contact_book.add(
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
contact_book.metadata.options['groups'] = {
    'options_type': 'local_flat',
    'values': ['family', 'friends', 'work', 'other']
}
contact_book.metadata.validations['phone_regex'] = RegexTextValidation(r'\d{7}')
