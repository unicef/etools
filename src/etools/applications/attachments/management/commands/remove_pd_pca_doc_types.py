from django.core.management.base import BaseCommand

from unicef_attachments.models import Attachment, FileType

from etools.libraries.tenant_support.utils import run_on_all_tenants


class Command(BaseCommand):
    """Remove PD/PCA document types"""

    def run(self):
        mapping = [
            ("pd", "signed_pd/ssfa"),
            ("pca", "attached_agreement"),
        ]
        for from_filetype_name, to_filetype_name in mapping:
            try:
                from_filetype = FileType.objects.filter(
                    name=from_filetype_name
                )
                to_filetype = FileType.objects.get(name=to_filetype_name)
                for attachment in Attachment.objects.filter(file_type__in=from_filetype):
                    attachment.filetype = to_filetype
                    attachment.save()
                for filetype in from_filetype:
                    filetype.delete()
            except FileType.DoesNotExist:
                # schema may not have this file type so ignore
                pass

    def handle(self, *args, **options):
        run_on_all_tenants(self.run)
