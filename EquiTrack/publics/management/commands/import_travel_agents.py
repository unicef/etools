from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from publics.tasks import import_travel_agents


class Command(BaseCommand):
    """
    Usage:
    manage.py et2f_init [--with_users, --with_partners, --assign_sections, --with_offices] <username> <password>

    Username and password required to create a user for testing and look up the proper schema.

    -u | --with_users : Import sample users
    -o | --with_offices : Import sample offices
    -p | --with_partners : Import sample partners
    -s | --assign_sections : Assign all sections to the current schema !Use only on local dev machine!
    """

    def add_arguments(self, parser):
        parser.add_argument('xml_path', nargs=1)

    @atomic
    def handle(self, *args, **options):
        xml_path = options['xml_path']

        import_travel_agents(xml_path)
