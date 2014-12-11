__author__ = 'jcranwellward'

from django.core.management.base import BaseCommand, CommandError

from winter import tasks


class Command(BaseCommand):
    args = 'users, sites'
    help = 'Manage winter data'

    def handle(self, *args, **options):

        task = args[0]
        if task == 'users':
            tasks.set_users()

        if task == 'get_sites':
            tasks.get_sites()

        if task == 'set_sites':
            tasks.set_sites()

        if task == 'import':
            tasks.import_docs()

        if task == 'manifest':
            tasks.prepare_manifest()

        if task == 'full':
            tasks.import_docs()
            tasks.prepare_manifest()







