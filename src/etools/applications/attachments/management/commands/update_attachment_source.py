from django.core.management.base import BaseCommand

from unicef_attachments.models import Attachment
from unicef_attachments.utils import get_attachment_flat_model

from etools.applications.attachments.utils import get_source
from etools.libraries.tenant_support.utils import run_on_all_tenants


class Command(BaseCommand):
    """Denormalize all attachments"""

    def run(self):
        attachment_qs = get_attachment_flat_model().objects.filter(source="")
        for flat in attachment_qs:
            try:
                flat.source = get_source(flat.attachment)
                flat.save()
            except Attachment.DoesNotExist:
                pass

    def handle(self, *args, **options):
        run_on_all_tenants(self.run)
