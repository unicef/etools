
from django.db import models

from users.models import Country


class VisionSyncLog(models.Model):

    country = models.ForeignKey(Country)
    handler_name = models.CharField(max_length=50)
    total_records = models.IntegerField(default=0)
    total_processed = models.IntegerField(default=0)
    successful = models.BooleanField(default=False)
    exception_message = models.TextField(blank=True, null=True)
    date_processed = models.DateTimeField(auto_now=True)
