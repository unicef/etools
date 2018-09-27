from django.core.management.base import BaseCommand

from unicef_attachments.utils import get_attachment_flat_model

from etools.libraries.tenant_support.utils import run_on_all_tenants


class Command(BaseCommand):
    """Update object link in attachment flat model"""

    def run(self):
        for flat in get_attachment_flat_model().objects.all():
            try:
                flat.object_link = flat.attachment.content_object.get_object_url()
            except AttributeError:
                continue
            else:
                flat.save()

    def handle(self, *args, **options):
        run_on_all_tenants(self.run)
