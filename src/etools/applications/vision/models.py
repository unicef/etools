from django.db import models
from django.utils.translation import ugettext_lazy as _

from unicef_vision.models import AbstractVisionLog

from etools.applications.users.models import Country


class VisionSyncLog(AbstractVisionLog):
    country = models.ForeignKey(Country, verbose_name=_('Country'), on_delete=models.CASCADE)

    def __str__(self):
        return '{0.country} {0.date_processed}:{0.successful} {0.total_processed}'.format(self)
