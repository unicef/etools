from django.core.management.base import BaseCommand

from etools.applications.attachments.models import AttachmentFlat
from etools.applications.utils.common.utils import run_on_all_tenants


class Command(BaseCommand):
    """Update object link in attachment flat model"""

    def run(self):
        for flat in AttachmentFlat.objects.all():
            try:
                flat.object_link = flat.attachment.content_object.get_object_url()
            except AttributeError:
                continue
            else:
                flat.save()

    def handle(self, *args, **options):
        run_on_all_tenants(self.run)
