from django.core.management.base import BaseCommand

from unicef_attachments.models import Attachment
from unicef_attachments.utils import get_attachment_flat_model, get_denormalize_func

from etools.applications.utils.common.utils import run_on_all_tenants


class Command(BaseCommand):
    """Denormalize all attachments"""

    def run(self):
        attachment_qs = Attachment.objects.exclude(
            pk__in=get_attachment_flat_model().objects.values_list(
                "attachment_id",
                flat=True
            )
        )
        for attachment in attachment_qs:
            get_denormalize_func()(attachment)

    def handle(self, *args, **options):
        run_on_all_tenants(self.run)
