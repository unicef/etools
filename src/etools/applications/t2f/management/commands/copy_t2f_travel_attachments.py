from django.core.management.base import BaseCommand

from etools.applications.partners.utils import copy_t2f_travel_attachments
from etools.applications.utils.common.utils import run_on_all_tenants


class Command(BaseCommand):
    def handle(self, *args, **options):
        run_on_all_tenants(copy_t2f_travel_attachments, **options)
