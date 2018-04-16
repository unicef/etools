from django.core.management.base import BaseCommand

from attachments.models import Attachment
from attachments.utils import denormalize_attachment
from utils.common.utils import run_on_all_tenants


class Command(BaseCommand):
    """Denormalize all attachments"""
    def run(self):
        for attachment in Attachment.objects.all():
            denormalize_attachment(attachment)

    def handle(self, *args, **options):
        run_on_all_tenants(self.run)
