import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand

from etools.applications.publics.models import Currency

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ""

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            dest='all',
            default=False,
            help='select all options but `demo`')
        parser.add_argument(
            '--users',
            action='store_true',
            dest='users',
            default=False,
            help='')
        parser.add_argument(
            '--migrate',
            action='store_true',
            dest='migrate',
            default=False,
            help='select all production deployment options')
        parser.add_argument(
            '--fixtures',
            action='store_true',
            dest='fixtures',
            default=False,
            help='fixtures')
        parser.add_argument(
            '--notifications',
            action='store_true',
            dest='notifications',
            default=False,
            help='update notifications')
        parser.add_argument(
            '--permissions',
            action='store_true',
            dest='permissions',
            default=False,
            help='update permissions')

    def handle(self, *args, **options):
        verbosity = options['verbosity']
        migrate = options['migrate']
        _all = options['all']

        ModelUser = get_user_model()
        if migrate or _all:
            self.stdout.write("Run migrations")
            call_command('migrate_schemas', verbosity=verbosity - 1)

        logger.info('Be sure USD is present')
        Currency.objects.get_or_create(code='USD')

        if options['users'] or _all:
            logger.info('Create Admin and Groups')
            if settings.DEBUG:
                pwd = '123'
                admin = os.environ.get('USER', 'admin')
            else:
                pwd = os.environ.get('ADMIN_PASSWORD', ModelUser.objects.make_random_password())
                admin = os.environ.get('ADMIN_USERNAME', 'admin')

            self._admin_user, created = ModelUser.objects.get_or_create(username=admin,

                                                                        defaults={"email": f'{admin}@unicef.org',
                                                                                  "is_superuser": True,
                                                                                  "is_staff": True,
                                                                                  "password": make_password(pwd)})

            groups_name = ['Partnership Manager', 'Travel Administrator', 'Travel Focal Point', 'UNICEF User',
                           'Country Office Administrator']
            groups = []

            logger.info('Setup Groups')
            for group_name in groups_name:
                logger.info(f'Setup {group_name}')
                gr, _ = Group.objects.get_or_create(name=group_name)
                groups.append(gr)
            call_command('loaddata', 'audit_groups')
            call_command('loaddata', 'tpm_groups')
            call_command('loaddata', 'groups')

            self._admin_user.groups.set(groups)

            if created:  # pragma: no cover
                self.stdout.write(f"Created superuser `{admin}` with password `{pwd}`")
            else:  # pragma: no cover
                self.stdout.write(f"Superuser `{admin}` already exists`.")

        if options['notifications'] or _all:
            logger.info('Update Notifications')
            call_command('update_notifications')

        if options['fixtures'] or _all:
            logger.info('Update Fixtures')
            call_command('loaddata', 'action_points_categories')
            call_command('loaddata', 'audit_staff_organization')

        if options['permissions'] or _all:
            logger.info('Update Permissions')
            call_command('update_audit_permissions')
            call_command('update_tpm_permissions')
            call_command('update_action_points_permissions')
