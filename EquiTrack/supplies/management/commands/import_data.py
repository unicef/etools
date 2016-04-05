__author__ = 'Tarek'


from django.core.management.base import BaseCommand

from supplies.tasks import import_docs


class Command(BaseCommand):

    can_import_settings = True

    def handle(self, **options):

        import_docs()





