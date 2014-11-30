__author__ = 'jcranwellward'

from django.core.management.base import BaseCommand, CommandError

import tasks


class Command(BaseCommand):
    args = 'users, sites'
    help = 'Manage winter data'

    def handle(self, *args, **options):

        task = args[0]
        if task == 'users':
            tasks.set_users()
        if task == 'sites':
            tasks.set_sites()
        if task == 'import':
            tasks.import_docs()






