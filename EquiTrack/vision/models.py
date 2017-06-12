
from django.db import models

from users.models import Country


class VisionSyncLog(models.Model):
    """
    Represents a sync log for Vision SAP sync

    Relates to :model:`users.Country`
    """

    country = models.ForeignKey(Country)
    handler_name = models.CharField(max_length=50)
    total_records = models.IntegerField(default=0)
    total_processed = models.IntegerField(default=0)
    successful = models.BooleanField(default=False)
    details = models.CharField(max_length=2048, blank=True, null=True)
    exception_message = models.TextField(blank=True, null=True)
    date_processed = models.DateTimeField(auto_now=True)
