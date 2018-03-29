from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from users.models import Country


@python_2_unicode_compatible
class VisionSyncLog(models.Model):
    """
    Represents a sync log for Vision SAP sync

    Relates to :model:`users.Country`
    """

    country = models.ForeignKey(Country, verbose_name=_('Country'))
    handler_name = models.CharField(max_length=50, verbose_name=_('Handler Name'))
    total_records = models.IntegerField(default=0, verbose_name=_('Total Records'))
    total_processed = models.IntegerField(default=0, verbose_name=_('Total Processed'))
    successful = models.BooleanField(default=False, verbose_name=_('Successful'))
    details = models.CharField(max_length=2048, blank=True, default='', verbose_name=_('Details'))
    exception_message = models.TextField(blank=True, default='', verbose_name=_('Exception Message'))
    date_processed = models.DateTimeField(auto_now=True, verbose_name=_('Date Processed'))

    def __str__(self):
        return u'{0.country} {0.date_processed}:{0.successful} {0.total_processed}'.format(self)
