from django.core.management.base import BaseCommand

from etools.applications.attachments.models import Attachment, AttachmentFlat
from etools.applications.attachments.utils import denormalize_attachment
from etools.applications.utils.common.utils import run_on_all_tenants


class Command(BaseCommand):
    """Denormalize all attachments"""

    def run(self):
        attachment_qs = Attachment.objects.exclude(
            pk__in=AttachmentFlat.objects.values_list(
                "attachment_id",
                flat=True
            )
        )
        for attachment in attachment_qs:
            denormalize_attachment(attachment)

    def handle(self, *args, **options):
        run_on_all_tenants(self.run)
