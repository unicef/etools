from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.transaction import atomic

from users.models import Country


class Command(BaseCommand):
    """
    Usage:
    manage.py import_dsa <country_name> <csv_path>

    Country name must be a valid schema name.
    CSV path must be a valid path to the csv file containing the dsa rates
    """

    def add_arguments(self, parser):
        parser.add_argument('country_name', nargs=1)
        parser.add_argument('import_file_path', nargs=1)

    @atomic
    def handle(self, *args, **options):
        country_name = options['country_name'][0]

        self.stdout.write(country_name)
        country = Country.objects.get(name=country_name)
        connection.set_tenant(country)

        # if not import_file_path:
        #     self.stderr.write('Invalid file path')
        #     return
        #
        # with open(import_file_path, 'r') as fp:
        #     raw_json = fp.read()
        #
        # data = json.loads(raw_json)
        #
        # for user_type in data:
        #     user_data = data['user_type']
        #     for status in user_data:

        model_field_mapping = {'status': None,
                               'trip_reference_number': None,
                               'action_point_number': None,
                               'description': None,
                               'due_date': None,
                               'actions_taken': None,
                               'created_at': None,
                               'comments': None,
                               'completed_at': None,
                               'follow_up': None,
                               'person_responsible': None,
                               'id': None}

        self.stdout.write('Regenerating permission matrix')
        permissions = {}
        for user_type in ['Assigner', 'PersonResponsible', 'Others', 'PME']:
            permissions[user_type] = model_field_mapping.copy()
            for k in permissions[user_type]:
                permissions[user_type][k] = {'edit': False,
                                             'view': True}
