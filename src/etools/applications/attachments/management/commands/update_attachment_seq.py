from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Max

from etools.applications.utils.common.utils import run_on_all_tenants

from unicef_attachments.models import Attachment


class Command(BaseCommand):
    """Update seq value for attachment model"""

    def run(self):
        # get max id for attachments
        # update seq value to match this
        row = Attachment.objects.aggregate(max_id=Max("id"))
        cursor = connection.cursor()
        cursor.execute(
            "SELECT setval('unicef_attachments_attachment_id_seq', {}, TRUE)".format(
                row["max_id"]
            )
        )

    def handle(self, *args, **options):
        run_on_all_tenants(self.run)
