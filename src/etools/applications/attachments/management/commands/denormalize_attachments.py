from django.core.management.base import BaseCommand

from unicef_attachments.models import Attachment
from unicef_attachments.utils import get_attachment_flat_model, get_denormalize_func

from etools.libraries.tenant_support.utils import run_on_all_tenants


class Command(BaseCommand):
    """Denormalize all attachments"""
    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            dest="all",
            help="Process all attachments"
        )

    def run(self):
        attachment_qs = Attachment.objects

        if not self.all_flag:
            attachment_qs = attachment_qs.exclude(
                pk__in=get_attachment_flat_model().objects.values_list(
                    "attachment_id",
                    flat=True
                )
            )

        for attachment in attachment_qs.all():
            get_denormalize_func()(attachment)

    def handle(self, *args, **options):
        self.all_flag = options["all"]
        run_on_all_tenants(self.run)
