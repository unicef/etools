from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel

from etools.applications.reports.models import ResultType


class CPOutputConfig(TimeStampedModel):
    cp_output = models.OneToOneField('reports.Result', related_name='fm_config',
                                     verbose_name=_('CP Output To Be Monitored'))
    is_monitored = models.BooleanField(default=True, verbose_name=_('Monitored At Community Level?'))
    is_priority = models.BooleanField(verbose_name=_('Priority?'), default=False)
    government_partners = models.ManyToManyField('partners.PartnerOrganization', blank=True,
                                                 verbose_name=_('Contributing Government Partners'))

    def __str__(self):
        if self.cp_output.result_type.name == ResultType.OUTPUT:
            return self.cp_output.output_name
        return self.cp_output.result_name
